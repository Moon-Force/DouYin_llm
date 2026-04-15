from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 保持一个薄入口，方便直接用 `python tests/verify_memory_pipeline.py` 执行。
from tests.memory_pipeline_verifier.runner import main


if __name__ == "__main__":
    raise SystemExit(main())
