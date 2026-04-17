import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import Settings, load_dotenv


class LocalMemoryModelSettingsTests(unittest.TestCase):
    def test_load_dotenv_does_not_override_existing_environment_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv_path = Path(tmpdir) / ".env"
            dotenv_path.write_text("MEMORY_EXTRACTOR_MODE=local\n", encoding="utf-8")

            with patch.dict(os.environ, {"MEMORY_EXTRACTOR_MODE": "remote"}, clear=True):
                load_dotenv(str(dotenv_path))
                loaded = os.environ["MEMORY_EXTRACTOR_MODE"]

            self.assertEqual(loaded, "remote")

    def test_memory_extractor_defaults_use_global_user_directory(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"}, clear=True):
            settings = Settings()

        expected_dir = Path(r"C:\Users\tester\AppData\Local") / "DouYinLLM" / "models" / "memory_extractor"
        self.assertFalse(settings.memory_extractor_enabled)
        self.assertEqual(settings.memory_extractor_mode, "local")
        self.assertEqual(settings.memory_extractor_model_path, expected_dir)
        self.assertEqual(
            settings.memory_extractor_model_file_path,
            expected_dir / settings.memory_extractor_model_filename,
        )
        self.assertNotEqual(settings.memory_extractor_model_path, settings.data_dir / "models" / "memory_extractor")
        self.assertEqual(settings.memory_extractor_context_size, 4096)
        self.assertEqual(settings.memory_extractor_max_tokens, 512)
        self.assertEqual(settings.memory_extractor_timeout_seconds, 30.0)
        self.assertGreaterEqual(settings.memory_extractor_threads, 1)

    def test_memory_extractor_env_override_is_evaluated_at_instantiation(self):
        env = {
            "MEMORY_EXTRACTOR_ENABLED": "true",
            "MEMORY_EXTRACTOR_MODE": "remote",
            "MEMORY_EXTRACTOR_MODEL_PATH": r"D:\models\extractor",
            "MEMORY_EXTRACTOR_MODEL_URL": "https://example.test/model.gguf",
            "MEMORY_EXTRACTOR_MODEL_FILENAME": "extractor.gguf",
            "MEMORY_EXTRACTOR_CONTEXT_SIZE": "8192",
            "MEMORY_EXTRACTOR_MAX_TOKENS": "768",
            "MEMORY_EXTRACTOR_TIMEOUT_SECONDS": "45.5",
            "MEMORY_EXTRACTOR_THREADS": "6",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        self.assertTrue(settings.memory_extractor_enabled)
        self.assertEqual(settings.memory_extractor_mode, "remote")
        self.assertEqual(settings.memory_extractor_model_path, Path(r"D:\models\extractor"))
        self.assertEqual(settings.memory_extractor_model_url, "https://example.test/model.gguf")
        self.assertEqual(settings.memory_extractor_model_filename, "extractor.gguf")
        self.assertEqual(settings.memory_extractor_context_size, 8192)
        self.assertEqual(settings.memory_extractor_max_tokens, 768)
        self.assertEqual(settings.memory_extractor_timeout_seconds, 45.5)
        self.assertEqual(settings.memory_extractor_threads, 6)

    def test_blank_numeric_env_values_fall_back_to_defaults(self):
        expected_threads = max(1, min(8, os.cpu_count() or 1))
        env = {
            "MEMORY_EXTRACTOR_THREADS": "",
            "MEMORY_EXTRACTOR_TIMEOUT_SECONDS": "",
            "MEMORY_EXTRACTOR_CONTEXT_SIZE": "",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        self.assertEqual(settings.memory_extractor_threads, expected_threads)
        self.assertEqual(settings.memory_extractor_timeout_seconds, 30.0)
        self.assertEqual(settings.memory_extractor_context_size, 4096)

    def test_ensure_dirs_creates_memory_extractor_model_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            env = {
                "DATA_DIR": str(base / "data"),
                "DATABASE_PATH": str(base / "data" / "live_prompter.db"),
                "CHROMA_DIR": str(base / "data" / "chroma"),
                "MEMORY_EXTRACTOR_MODEL_PATH": str(base / "global_models" / "memory_extractor"),
            }
            with patch.dict(os.environ, env, clear=True):
                settings = Settings()
                settings.ensure_dirs()

            self.assertTrue(settings.memory_extractor_model_path.exists())
            self.assertTrue(settings.memory_extractor_model_path.is_dir())

    def test_env_example_uses_blank_threads_to_keep_runtime_default(self):
        env_example = Path(__file__).resolve().parent.parent / ".env.example"
        lines = env_example.read_text(encoding="utf-8").splitlines()
        self.assertIn("MEMORY_EXTRACTOR_THREADS=", lines)


if __name__ == "__main__":
    unittest.main()
