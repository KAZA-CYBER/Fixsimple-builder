import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from task_runner import load_task


class TaskRunnerTests(unittest.TestCase):

    def test_load_valid_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"

            path.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-001",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "python3 test.py",
                        "max_repair_iterations": 2,
                    }
                )
            )

            task = load_task(path)

            self.assertEqual(task.task_id, "RUNNER-001")
            self.assertEqual(task.target_files, ["target.py"])
            self.assertEqual(task.max_repair_iterations, 2)

    def test_reject_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"

            path.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-002",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                        "invented_permission": True,
                    }
                )
            )

            with self.assertRaises(ValueError):
                load_task(path)


if __name__ == "__main__":
    unittest.main()
