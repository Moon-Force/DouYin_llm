import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small"):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
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
        )

        store.add_event(event)

        fake_embedding.embed_text.assert_called_once_with("阿明 今晚吃面吗")
        fake_collection.upsert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
