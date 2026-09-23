import tempfile
import unittest
from pathlib import Path

from src.task_contract import BuilderTask


class BuilderTaskTests(unittest.TestCase):

    def test_valid_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example.py").write_text("x = 1\n")

            task = BuilderTask(
                task_id="V0-TEST-001",
                instruction="Change x to 2",
                target_files=["example.py"],
                verification_command="python3 example.py",
            )

            task.validate(root)

    def test_rejects_repo_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            task = BuilderTask(
                task_id="V0-TEST-002",
                instruction="Bad path",
                target_files=["../outside.py"],
                verification_command="true",
            )

            with self.assertRaises(ValueError):
                task.validate(root)

    def test_rejects_protected_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "protected.py").write_text("x = 1\n")

            task = BuilderTask(
                task_id="V0-TEST-003",
                instruction="Modify protected file",
                target_files=["protected.py"],
                verification_command="true",
                protected_paths=["protected.py"],
            )

            with self.assertRaises(PermissionError):
                task.validate(root)


if __name__ == "__main__":
    unittest.main()
