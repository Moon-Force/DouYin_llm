"""Rebuild Chroma memory indexes from SQLite source data."""

import argparse
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from itertools import islice
from pathlib import Path

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import VectorMemory


logger = logging.getLogger(__name__)


def chunked(values, size):
    iterator = iter(values)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


@contextmanager
def open_rebuild_connection(long_term_store):
    has_instance_connect = "_connect" in getattr(long_term_store, "__dict__", {})
    has_class_connect = hasattr(type(long_term_store), "_connect")
    if has_instance_connect or has_class_connect:
        with long_term_store._connect() as connection:
            yield connection
        return

    connection = sqlite3.connect(str(long_term_store.database_path))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def fetch_memory_rows(long_term_store, room_id="", limit=None):
    clauses = []
    params = []
    if room_id:
        clauses.append("room_id = ?")
        params.append(room_id)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = " LIMIT ?" if limit else ""
    if limit:
        params.append(int(limit))

    with open_rebuild_connection(long_term_store) as connection:
        rows = connection.execute(
            f"""
            SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type, confidence, updated_at
            FROM viewer_memories
            {where_clause}
            ORDER BY updated_at DESC{limit_clause}
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def build_memory_collection_name(vector_memory):
    return f"viewer_memories_{vector_memory._collection_suffix}"


def manifest_path(settings):
    return Path(settings.chroma_dir) / "index_manifest.json"


def load_manifest(settings):
    path = manifest_path(settings)
    if not path.exists():
        return {"active_signature": "", "updated_at": 0, "collections": {}}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to read embedding manifest at %s; recreating it", path)
        return {"active_signature": "", "updated_at": 0, "collections": {}}


def save_manifest(settings, manifest):
    path = manifest_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def update_manifest(settings, result):
    manifest = load_manifest(settings)
    now = time.time_ns() // 1_000_000
    signature = settings.embedding_signature()
    manifest["active_signature"] = signature
    manifest["updated_at"] = now
    collections = manifest.setdefault("collections", {})

    if "memories" in result:
        item = result["memories"]
        collections[item["collection"]] = {
            "target": "memories",
            "embedding_mode": settings.embedding_mode,
            "embedding_model": settings.embedding_model,
            "collection_name": item["collection"],
            "rebuilt_at": now,
            "count": item["count"],
        }

    save_manifest(settings, manifest)
    return manifest


def rebuild_memory_collection(long_term_store, embedding_service, vector_memory, room_id="", limit=None, dry_run=False, drop_existing=False):
    rows = fetch_memory_rows(long_term_store, room_id=room_id, limit=limit)
    result = {
        "collection": build_memory_collection_name(vector_memory),
        "count": len(rows),
    }
    if dry_run or not rows:
        return result

    if drop_existing and getattr(vector_memory, "_client", None):
        logger.warning(
            "Dropping existing collection before rebuild: collection=%s signature=%s",
            result["collection"],
            vector_memory._collection_suffix,
        )
        vector_memory._client.delete_collection(result["collection"])
        vector_memory.memory_collection = vector_memory._client.get_or_create_collection(result["collection"])

    for batch in chunked(rows, 64):
        texts = [row["memory_text"] for row in batch]
        embeddings = embedding_service.embed_texts(texts)
        vector_memory.memory_collection.upsert(
            ids=[row["memory_id"] for row in batch],
            documents=texts,
            metadatas=[
                {
                    "room_id": row["room_id"],
                    "viewer_id": row["viewer_id"],
                    "memory_type": row["memory_type"],
                    "source_event_id": row["source_event_id"] or "",
                    "confidence": row["confidence"],
                    "updated_at": row["updated_at"],
                }
                for row in batch
            ],
            embeddings=embeddings,
        )
    return result


def rebuild_embeddings(
    *,
    settings=settings,
    long_term_store=None,
    embedding_service=None,
    vector_memory=None,
    target="memories",
    room_id="",
    limit=None,
    dry_run=False,
    drop_existing=False,
):
    if target != "memories":
        raise ValueError("Only memories target is supported")

    long_term_store = long_term_store or LongTermStore(settings.database_path)
    embedding_service = embedding_service or EmbeddingService(settings)
    vector_memory = vector_memory or VectorMemory(settings.chroma_dir, settings=settings, embedding_service=embedding_service)

    if getattr(vector_memory, "_client", None) is None and hasattr(vector_memory, "collection"):
        vector_memory._client = None

    result = {"target": target}
    result["memories"] = rebuild_memory_collection(
        long_term_store,
        embedding_service,
        vector_memory,
        room_id=room_id,
        limit=limit,
        dry_run=dry_run,
        drop_existing=drop_existing,
    )
    if not dry_run:
        result["manifest"] = update_manifest(settings, result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Rebuild memory embedding indexes from SQLite source data.")
    parser.add_argument("--target", choices=["memories"], default="memories")
    parser.add_argument("--room-id", default="")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--drop-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = rebuild_embeddings(
        target=args.target,
        room_id=args.room_id,
        limit=args.limit,
        dry_run=args.dry_run,
        drop_existing=args.drop_existing,
    )
    logger.info("Embedding rebuild result: %s", result)


if __name__ == "__main__":
    main()
