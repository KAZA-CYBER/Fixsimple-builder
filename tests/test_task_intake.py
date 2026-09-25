import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from task_intake import prepare_task_intake


class TaskIntakeTests(unittest.TestCase):

    def test_existing_targets_use_legacy_task_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.py").write_text("x = 1\n")

            result = prepare_task_intake(
                root,
                {
                    "task_id": "INTAKE-001",
                    "instruction": "Repair target.",
                    "target_files": ["target.py"],
                    "verification_command": "true",
                },
            )

            self.assertFalse(
                result.discovery_required
            )
            self.assertIsNotNone(result.task)
            self.assertEqual(
                result.task.target_files,
                ["target.py"],
            )
            self.assertEqual(
                result.candidate_files,
                [],
            )

    def test_missing_targets_returns_repository_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "src").mkdir()
            (root / "tests").mkdir()

            (root / "src" / "app.py").write_text(
                "x = 1\n"
            )
            (root / "tests" / "test_app.py").write_text(
                "pass\n"
            )

            result = prepare_task_intake(
                root,
                {
                    "task_id": "INTAKE-002",
                    "instruction": "Repair the application.",
                    "verification_command": "true",
                },
            )

            self.assertTrue(
                result.discovery_required
            )
            self.assertIsNone(result.task)
            self.assertEqual(
                result.candidate_files,
                [
                    "src/app.py",
                    "tests/test_app.py",
                ],
            )


if __name__ == "__main__":
    unittest.main()
