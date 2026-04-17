import builtins
import importlib
import os
import sys
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


class LocalMemoryExtractionRuntimeTests(unittest.TestCase):
    def test_resolve_model_path_uses_settings_file_path_for_dot_directory(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models" / "v1.0"
            model_file = model_dir / "extractor.gguf"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file.write_bytes(b"existing")

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                },
                clear=True,
            ):
                settings = Settings()

            runtime = LocalMemoryExtractionModel(settings=settings)
            resolved = runtime.resolve_model_path()

            self.assertEqual(resolved, model_file)

    def test_resolve_model_path_reuses_existing_model_without_download(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file.write_bytes(b"existing")

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                },
                clear=True,
            ):
                settings = Settings()

            def downloader(_url, _destination):
                raise AssertionError("downloader should not be called when model already exists")

            runtime = LocalMemoryExtractionModel(settings=settings, downloader=downloader)
            resolved = runtime.resolve_model_path()

            self.assertEqual(resolved, model_file)
            self.assertTrue(resolved.exists())

    def test_resolve_model_path_downloads_when_missing_and_url_provided(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"
            calls = []

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                    "MEMORY_EXTRACTOR_MODEL_URL": "https://example.test/extractor.gguf",
                },
                clear=True,
            ):
                settings = Settings()

            def downloader(url, destination):
                calls.append((url, destination))
                Path(destination).write_bytes(b"downloaded")

            runtime = LocalMemoryExtractionModel(settings=settings, downloader=downloader)
            resolved = runtime.resolve_model_path()

            self.assertEqual(resolved, model_file)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "https://example.test/extractor.gguf")
            self.assertEqual(Path(calls[0][1]), model_file)
            self.assertEqual(model_file.read_bytes(), b"downloaded")

    def test_infer_json_uses_cached_runtime_and_returns_text_content(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file.write_bytes(b"existing")
            runtime_calls = []
            completion_calls = []

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                    "MEMORY_EXTRACTOR_CONTEXT_SIZE": "1024",
                    "MEMORY_EXTRACTOR_THREADS": "4",
                    "MEMORY_EXTRACTOR_MAX_TOKENS": "256",
                },
                clear=True,
            ):
                settings = Settings()

            class FakeRuntime:
                def create_chat_completion(self, **kwargs):
                    completion_calls.append(kwargs)
                    return {"choices": [{"message": {"content": '{"ok":true}'}}]}

            def llama_factory(**kwargs):
                runtime_calls.append(kwargs)
                return FakeRuntime()

            model = LocalMemoryExtractionModel(settings=settings, llama_factory=llama_factory)
            first = model.infer_json(system_prompt="sys-1", user_prompt="user-1")
            second = model.infer_json(system_prompt="sys-2", user_prompt="user-2")

        self.assertEqual(first, '{"ok":true}')
        self.assertEqual(second, '{"ok":true}')
        self.assertEqual(len(runtime_calls), 1)
        self.assertEqual(runtime_calls[0]["model_path"], str(model_file))
        self.assertEqual(runtime_calls[0]["n_ctx"], 1024)
        self.assertEqual(runtime_calls[0]["n_threads"], 4)
        self.assertEqual(len(completion_calls), 2)
        self.assertEqual(completion_calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(completion_calls[0]["max_tokens"], 256)
        self.assertEqual(completion_calls[0]["messages"][0]["content"], "sys-1")
        self.assertEqual(completion_calls[0]["messages"][1]["content"], "user-1")

    def test_import_does_not_require_llama_cpp_at_module_import_time(self):
        module_name = "backend.services.local_memory_model"
        sys.modules.pop(module_name, None)
        original_import = builtins.__import__

        def import_without_llama(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "llama_cpp":
                raise ModuleNotFoundError("No module named llama_cpp")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=import_without_llama):
            module = importlib.import_module(module_name)

        self.assertTrue(hasattr(module, "LocalMemoryExtractionModel"))

    def test_resolve_model_path_rejects_existing_directory_configured_as_file_path(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_model_dir = Path(tmpdir) / "extractor.gguf"
            fake_model_dir.mkdir(parents=True, exist_ok=True)

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(fake_model_dir),
                },
                clear=True,
            ):
                settings = Settings()

            runtime = LocalMemoryExtractionModel(settings=settings)
            with self.assertRaises(FileNotFoundError):
                runtime.resolve_model_path()

    def test_resolve_model_path_raises_if_download_result_is_not_file(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                    "MEMORY_EXTRACTOR_MODEL_URL": "https://example.test/extractor.gguf",
                },
                clear=True,
            ):
                settings = Settings()

            def downloader(_url, destination):
                Path(destination).mkdir(parents=True, exist_ok=True)

            runtime = LocalMemoryExtractionModel(settings=settings, downloader=downloader)
            with self.assertRaises(FileNotFoundError):
                runtime.resolve_model_path()

    def test_resolve_model_path_rejects_existing_empty_model_file(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file.write_bytes(b"")

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                },
                clear=True,
            ):
                settings = Settings()

            runtime = LocalMemoryExtractionModel(settings=settings)
            with self.assertRaises(FileNotFoundError):
                runtime.resolve_model_path()

    def test_resolve_model_path_raises_if_download_result_is_empty_file(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                    "MEMORY_EXTRACTOR_MODEL_URL": "https://example.test/extractor.gguf",
                },
                clear=True,
            ):
                settings = Settings()

            def downloader(_url, destination):
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                Path(destination).write_bytes(b"")

            runtime = LocalMemoryExtractionModel(settings=settings, downloader=downloader)
            with self.assertRaises(FileNotFoundError):
                runtime.resolve_model_path()

    def test_infer_json_raises_runtime_error_when_llama_cpp_missing(self):
        from backend.services.local_memory_model import LocalMemoryExtractionModel

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            model_file = model_dir / "extractor.gguf"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file.write_bytes(b"existing")

            with patch.dict(
                os.environ,
                {
                    "MEMORY_EXTRACTOR_MODEL_PATH": str(model_dir),
                    "MEMORY_EXTRACTOR_MODEL_FILENAME": model_file.name,
                },
                clear=True,
            ):
                settings = Settings()

            original_import = builtins.__import__

            def import_without_llama(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "llama_cpp":
                    raise ModuleNotFoundError("No module named llama_cpp")
                return original_import(name, globals, locals, fromlist, level)

            runtime = LocalMemoryExtractionModel(settings=settings)
            with patch("builtins.__import__", side_effect=import_without_llama):
                with self.assertRaises(RuntimeError):
                    runtime.infer_json(system_prompt="sys", user_prompt="user")


if __name__ == "__main__":
    unittest.main()
