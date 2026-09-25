import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from repository_inspector import inspect_repository


class RepositoryInspectorTests(unittest.TestCase):

    def test_inspects_relevant_files_and_ignores_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "runs" / "old").mkdir(parents=True)
            (root / "models").mkdir()
            (root / "__pycache__").mkdir()

            (root / "src" / "app.py").write_text("print('x')\n")
            (root / "tests" / "test_app.py").write_text("pass\n")
            (root / "config.json").write_text("{}\n")
            (root / "README.md").write_text("# Repo\n")

            (root / "runs" / "old" / "run.json").write_text("{}\n")
            (root / "models" / "model.json").write_text("{}\n")
            (root / "__pycache__" / "cache.py").write_text("x = 1\n")
            (root / "binary.bin").write_bytes(b"\x00\x01")

            result = inspect_repository(root)

            self.assertEqual(
                result,
                [
                    "README.md",
                    "config.json",
                    "src/app.py",
                    "tests/test_app.py",
                ],
            )


if __name__ == "__main__":
    unittest.main()
