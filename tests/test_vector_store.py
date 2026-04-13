import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small"):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
        semantic_event_min_score=0.35,
        semantic_memory_min_score=0.35,
        semantic_event_query_limit=8,
        semantic_memory_query_limit=6,
        semantic_final_k=3,
    )


class VectorMemoryTests(unittest.TestCase):
    def test_collection_names_use_embedding_signature(self):
        fake_client = MagicMock()
        fake_client.get_or_create_collection.side_effect = [MagicMock(), MagicMock()]
        fake_embedding = MagicMock()

        with patch("backend.memory.vector_store.chromadb") as chromadb_mock:
            chromadb_mock.PersistentClient.return_value = fake_client
            VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)

        fake_client.get_or_create_collection.assert_any_call("live_history_cloud_text_embedding_3_small")
        fake_client.get_or_create_collection.assert_any_call("viewer_memories_cloud_text_embedding_3_small")

    def test_add_event_uses_embedding_service(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.collection = fake_collection

        event = SimpleNamespace(
            event_id="evt-1",
            room_id="room-1",
            event_type="comment",
            content="今晚吃面吗",
            user=SimpleNamespace(nickname="阿明"),
            ts=123,
        )

        store.add_event(event)

        fake_embedding.embed_text.assert_called_once_with("阿明 今晚吃面吗")
        fake_collection.upsert.assert_called_once()

    def test_similar_returns_structured_results_and_applies_threshold(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["evt-1", "evt-2"]],
            "documents": [["阿明 今晚吃面吗", "阿明 你好"]],
            "metadatas": [[
                {"room_id": "room-1", "event_type": "comment", "nickname": "阿明", "ts": 200},
                {"room_id": "room-1", "event_type": "comment", "nickname": "阿明", "ts": 100},
            ]],
            "distances": [[0.2, 5.0]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.collection = fake_collection

        result = store.similar("吃面", room_id="room-1", limit=2)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "evt-1")
        self.assertEqual(result[0]["text"], "阿明 今晚吃面吗")
        self.assertEqual(result[0]["metadata"]["ts"], 200)

    def test_similar_memories_prefers_higher_confidence_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m1", "m2"]],
            "documents": [["喜欢拉面", "喜欢面食"]],
            "metadatas": [[
                {"room_id": "room-1", "viewer_id": "viewer-1", "memory_type": "preference", "confidence": 0.9, "updated_at": 200, "recall_count": 2},
                {"room_id": "room-1", "viewer_id": "viewer-1", "memory_type": "preference", "confidence": 0.4, "updated_at": 300, "recall_count": 1},
            ]],
            "distances": [[0.6, 0.59]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("喜欢吃面", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m1")


if __name__ == "__main__":
    unittest.main()
