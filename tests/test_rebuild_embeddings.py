import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.memory.rebuild_embeddings import rebuild_embeddings


def make_settings(signature="cloud_bge_m3"):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
        database_path=Path("data/live_prompter.db"),
        chroma_dir=Path("data/chroma"),
        embedding_mode="cloud",
        embedding_model="bge-m3",
    )


class RebuildEmbeddingsTests(unittest.TestCase):
    def test_dry_run_reports_memory_counts_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE events (
                    event_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    source_room_id TEXT,
                    session_id TEXT,
                    platform TEXT NOT NULL,
                    viewer_id TEXT,
                    event_type TEXT NOT NULL,
                    method TEXT NOT NULL,
                    livename TEXT NOT NULL,
                    user_id TEXT,
                    short_id TEXT,
                    sec_uid TEXT,
                    nickname TEXT,
                    content TEXT,
                    gift_name TEXT,
                    gift_id TEXT,
                    gift_count INTEGER NOT NULL DEFAULT 0,
                    gift_diamond_count INTEGER NOT NULL DEFAULT 0,
                    ts INTEGER NOT NULL,
                    metadata_json TEXT,
                    raw_json TEXT
                );
                """
            )
            conn.execute(
                """
                INSERT INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("m1", "room-1", "viewer-1", "evt-1", "likes ramen", "preference", 0.9, 1, 2, None, 0),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, room_id, source_room_id, session_id, platform, viewer_id, event_type, method,
                    livename, user_id, short_id, sec_uid, nickname, content, gift_name, gift_id,
                    gift_count, gift_diamond_count, ts, metadata_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-1",
                    "room-1",
                    "source-room-1",
                    "session-1",
                    "douyin",
                    "viewer-1",
                    "comment",
                    "WebcastChatMessage",
                    "test-room",
                    "user-1",
                    "",
                    "",
                    "A-Ming",
                    "hello",
                    "",
                    "",
                    0,
                    0,
                    123,
                    json.dumps({}),
                    json.dumps({}),
                ),
            )
            conn.commit()
            conn.close()

            fake_store = MagicMock()
            fake_store.database_path = db_path
            fake_embedding = MagicMock()
            fake_vector_memory = MagicMock()
            fake_vector_memory._collection_suffix = "cloud_bge_m3"

            result = rebuild_embeddings(
                settings=make_settings(),
                long_term_store=fake_store,
                embedding_service=fake_embedding,
                vector_memory=fake_vector_memory,
                target="memories",
                dry_run=True,
            )

        self.assertEqual(result["target"], "memories")
        self.assertEqual(result["memories"]["count"], 1)
        self.assertNotIn("events", result)
        fake_embedding.embed_texts.assert_not_called()
        fake_vector_memory.memory_collection.upsert.assert_not_called()
        self.assertNotIn("manifest", result)

    def test_rebuild_memories_drops_existing_collection_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            chroma_dir = Path(tmpdir) / "chroma"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                INSERT INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("m1", "room-1", "viewer-1", "evt-1", "likes ramen", "preference", 0.9, 1, 2, None, 0),
            )
            conn.commit()
            conn.close()

            fake_store = MagicMock()
            fake_store.database_path = db_path
            fake_client = MagicMock()
            fake_collection = MagicMock()
            fake_client.get_or_create_collection.return_value = fake_collection
            fake_embedding = MagicMock()
            fake_embedding.embed_texts.return_value = [[0.1, 0.2]]
            fake_vector_memory = MagicMock()
            fake_vector_memory._collection_suffix = "cloud_bge_m3"
            fake_vector_memory.memory_collection = fake_collection
            fake_vector_memory._client = fake_client
            local_settings = make_settings()
            local_settings.database_path = db_path
            local_settings.chroma_dir = chroma_dir

            result = rebuild_embeddings(
                settings=local_settings,
                long_term_store=fake_store,
                embedding_service=fake_embedding,
                vector_memory=fake_vector_memory,
                target="memories",
                drop_existing=True,
            )

        fake_client.delete_collection.assert_called_once_with("viewer_memories_cloud_bge_m3")
        fake_client.get_or_create_collection.assert_called_with("viewer_memories_cloud_bge_m3")
        fake_collection.upsert.assert_called_once()
        self.assertEqual(result["memories"]["count"], 1)

    def test_rebuild_writes_manifest_for_real_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            chroma_dir = Path(tmpdir) / "chroma"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                INSERT INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("m1", "room-1", "viewer-1", "evt-1", "likes ramen", "preference", 0.9, 1, 2, None, 0),
            )
            conn.commit()
            conn.close()

            fake_store = MagicMock()
            fake_store.database_path = db_path
            fake_client = MagicMock()
            fake_collection = MagicMock()
            fake_client.get_or_create_collection.return_value = fake_collection
            fake_embedding = MagicMock()
            fake_embedding.embed_texts.return_value = [[0.1, 0.2]]
            fake_vector_memory = MagicMock()
            fake_vector_memory._collection_suffix = "cloud_bge_m3"
            fake_vector_memory.memory_collection = fake_collection
            fake_vector_memory._client = fake_client
            local_settings = make_settings()
            local_settings.database_path = db_path
            local_settings.chroma_dir = chroma_dir

            result = rebuild_embeddings(
                settings=local_settings,
                long_term_store=fake_store,
                embedding_service=fake_embedding,
                vector_memory=fake_vector_memory,
                target="memories",
            )

            manifest = json.loads((chroma_dir / "index_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("manifest", result)
        self.assertEqual(manifest["active_signature"], "cloud_bge_m3")
        self.assertEqual(
            manifest["collections"]["viewer_memories_cloud_bge_m3"]["count"],
            1,
        )

    def test_strict_mode_rebuild_raises_when_embedding_generation_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            chroma_dir = Path(tmpdir) / "chroma"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                INSERT INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("m1", "room-1", "viewer-1", "evt-1", "likes ramen", "preference", 0.9, 1, 2, None, 0),
            )
            conn.commit()
            conn.close()

            fake_store = MagicMock()
            fake_store.database_path = db_path
            fake_embedding = MagicMock()
            fake_embedding.embed_texts.side_effect = RuntimeError("Embedding strict mode blocked fallback")
            fake_collection = MagicMock()
            fake_vector_memory = MagicMock()
            fake_vector_memory._collection_suffix = "cloud_bge_m3"
            fake_vector_memory.memory_collection = fake_collection
            fake_vector_memory._client = MagicMock()
            local_settings = make_settings()
            local_settings.database_path = db_path
            local_settings.chroma_dir = chroma_dir
            local_settings.embedding_strict = True

            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                rebuild_embeddings(
                    settings=local_settings,
                    long_term_store=fake_store,
                    embedding_service=fake_embedding,
                    vector_memory=fake_vector_memory,
                    target="memories",
                )


if __name__ == "__main__":
    unittest.main()
