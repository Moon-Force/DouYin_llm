from pathlib import Path
import unittest


class StartFrontendScriptTests(unittest.TestCase):
    def test_uses_path_discovery_for_node_and_npm(self):
        script_path = Path(__file__).resolve().parents[1] / "start_frontend.ps1"
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("Get-Command node", script)
        self.assertIn("Get-Command npm.cmd", script)
        self.assertNotIn(r"C:\Program Files\nodejs\node.exe", script)
        self.assertNotIn(r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js", script)


if __name__ == "__main__":
    unittest.main()
