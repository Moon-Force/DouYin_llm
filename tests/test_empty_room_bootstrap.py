import asyncio
import importlib
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from unittest.mock import patch

import backend.config as config_module
from backend.services.collector import DouyinCollector


class EmptyRoomBootstrapTests(unittest.TestCase):
    def test_settings_default_room_id_is_empty_when_env_var_is_missing(self):
        reloaded = None
        env_without_room_id = {key: value for key, value in os.environ.items() if key != "ROOM_ID"}
        try:
            with patch("pathlib.Path.exists", return_value=False):
                with patch.dict("os.environ", env_without_room_id, clear=True):
                    reloaded = importlib.reload(config_module)
            self.assertEqual(reloaded.Settings().room_id, "")
        finally:
            importlib.reload(config_module)

    def test_collector_does_not_start_without_room_id(self):
        settings = config_module.Settings(room_id="")
        collector = DouyinCollector(settings, event_handler=AsyncMock())

        started = collector.start(asyncio.new_event_loop())

        self.assertFalse(started)
        self.assertIsNone(collector.thread)

    def test_switch_room_starts_collector_after_empty_room_boot(self):
        settings = config_module.Settings(room_id="")
        collector = DouyinCollector(settings, event_handler=AsyncMock())
        loop = asyncio.new_event_loop()

        collector.start(loop)

        with patch.object(collector, "_run"), patch.object(threading.Thread, "start", autospec=True) as start_mock:
            switched = collector.switch_room("32137571630")

        self.assertTrue(switched)
        self.assertEqual(settings.room_id, "32137571630")
        self.assertIs(collector.loop, loop)
        self.assertEqual(start_mock.call_count, 1)

    def test_run_uses_websocket_ping_frames_instead_of_text_ping_messages(self):
        settings = config_module.Settings(room_id="32137571630")
        collector = DouyinCollector(settings, event_handler=AsyncMock())
        fake_ws = unittest.mock.MagicMock()

        def fake_run_forever(*args, **kwargs):
            collector.stop_event.set()

        fake_ws.run_forever.side_effect = fake_run_forever

        with patch("backend.services.collector.websocket.WebSocketApp", return_value=fake_ws):
            collector._run()

        fake_ws.run_forever.assert_called_once_with(
            ping_interval=settings.collector_ping_interval_seconds
        )

    def test_backend_app_import_does_not_initialize_runtime_until_needed(self):
        fake_store = MagicMock()
        fake_store.list_all_viewer_memories.return_value = []
        fake_vector = MagicMock()
        fake_vector._collection_suffix = "cloud_bge_m3_latest"

        with patch.object(config_module.settings, "ensure_dirs") as ensure_dirs_mock, patch(
            "backend.services.broker.EventBroker"
        ) as broker_cls, patch(
            "backend.memory.session_memory.SessionMemory"
        ) as session_cls, patch(
            "backend.memory.long_term.LongTermStore", return_value=fake_store
        ) as long_term_cls, patch(
            "backend.memory.embedding_service.EmbeddingService"
        ) as embedding_cls, patch(
            "backend.memory.vector_store.VectorMemory", return_value=fake_vector
        ) as vector_cls, patch(
            "backend.services.agent.LivePromptAgent"
        ) as agent_cls, patch(
            "backend.services.collector.DouyinCollector"
        ) as collector_cls, patch(
            "backend.services.memory_extractor.ViewerMemoryExtractor"
        ) as extractor_cls, patch(
            "backend.memory.rebuild_embeddings.load_manifest",
            return_value={
                "active_signature": config_module.settings.embedding_signature(),
                "collections": {
                    "viewer_memories_cloud_bge_m3_latest": {
                        "collection_name": "viewer_memories_cloud_bge_m3_latest",
                        "count": 0,
                    }
                },
            },
        ) as manifest_mock:
            sys.modules.pop("backend.app", None)
            reloaded = importlib.import_module("backend.app")

            ensure_dirs_mock.assert_not_called()
            broker_cls.assert_not_called()
            session_cls.assert_not_called()
            long_term_cls.assert_not_called()
            embedding_cls.assert_not_called()
            vector_cls.assert_not_called()
            agent_cls.assert_not_called()
            collector_cls.assert_not_called()
            extractor_cls.assert_not_called()
            manifest_mock.assert_not_called()

            reloaded.ensure_runtime()

            ensure_dirs_mock.assert_called_once()
            broker_cls.assert_called_once()
            session_cls.assert_called_once()
            long_term_cls.assert_called_once()
            embedding_cls.assert_called_once()
            vector_cls.assert_called_once()
            agent_cls.assert_called_once()
            collector_cls.assert_called_once()
            extractor_cls.assert_called_once()
            manifest_mock.assert_called_once()
            fake_vector.prime_memory_index.assert_called_once_with([], force_rebuild=False)

        sys.modules.pop("backend.app", None)


if __name__ == "__main__":
    unittest.main()
