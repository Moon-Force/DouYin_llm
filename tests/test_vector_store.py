import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small", strict=False):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
        embedding_strict=strict,
        semantic_memory_min_score=0.35,
        semantic_memory_query_limit=6,
        semantic_final_k=3,
    )


class VectorMemoryTests(unittest.TestCase):
    def test_collection_names_only_create_viewer_memory_collection(self):
        fake_client = MagicMock()
        fake_client.get_or_create_collection.return_value = MagicMock()
        fake_embedding = MagicMock()

        with patch("backend.memory.vector_store.chromadb") as chromadb_mock:
            chromadb_mock.PersistentClient.return_value = fake_client
            store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)

        fake_client.get_or_create_collection.assert_called_once_with("viewer_memories_cloud_text_embedding_3_small")
        self.assertIsNone(store.collection)

    def test_similar_memories_prefers_higher_confidence_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m1", "m2"]],
            "documents": [["likes ramen", "likes noodles"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 2,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.4,
                    "updated_at": 300,
                    "recall_count": 1,
                },
            ]],
            "distances": [[0.6, 0.59]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("likes eating noodles", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_non_strict_mode_falls_back_to_token_matching_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=False), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "m1",
                "document": "likes ramen",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 1,
                },
            }
        ]

        result = store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_strict_mode_raises_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        with self.assertRaisesRegex(RuntimeError, "strict mode"):
            store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

    def test_strict_mode_marks_backend_not_ready_when_chroma_is_missing(self):
        with patch("backend.memory.vector_store.chromadb", None):
            store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=MagicMock())

        self.assertFalse(store.semantic_backend_ready())
        self.assertIn("Chroma", store.semantic_backend_reason())

    def test_add_memory_includes_status_source_and_pin_metadata(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memory = SimpleNamespace(
            memory_id="mem-1",
            room_id="room-1",
            viewer_id="viewer-1",
            source_event_id="evt-1",
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            confidence=0.91,
            updated_at=123,
            recall_count=2,
            status="active",
            source_kind="manual",
            is_pinned=True,
        )

        store.add_memory(memory)

        upsert_kwargs = fake_collection.upsert.call_args.kwargs
        self.assertEqual(upsert_kwargs["metadatas"][0]["status"], "active")
        self.assertEqual(upsert_kwargs["metadatas"][0]["source_kind"], "manual")
        self.assertEqual(upsert_kwargs["metadatas"][0]["is_pinned"], 1)

    def test_sync_memory_removes_deleted_or_invalid_entries(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "mem-1",
                "document": "喜欢拉面",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                },
            }
        ]

        store.sync_memory(
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="喜欢拉面",
                memory_type="preference",
                confidence=0.8,
                updated_at=20,
                recall_count=1,
                status="deleted",
                source_kind="auto",
                is_pinned=False,
            )
        )

        self.assertEqual(store._memory_items, [])
        fake_collection.delete.assert_called_once_with(ids=["mem-1"])

    def test_similar_memories_prefers_manual_and_pinned_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-auto", "m-manual"]],
            "documents": [["喜欢拉面", "喜欢拉面"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 100,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 90,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("喜欢拉面", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-manual")


if __name__ == "__main__":
    unittest.main()
