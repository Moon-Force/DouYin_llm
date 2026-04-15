import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small"):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
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


if __name__ == "__main__":
    unittest.main()
