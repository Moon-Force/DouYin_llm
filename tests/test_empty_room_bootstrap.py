import asyncio
import importlib
import os
import threading
import unittest
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


if __name__ == "__main__":
    unittest.main()
