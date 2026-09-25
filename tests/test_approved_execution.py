import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from approved_execution import execute_approved_run
from target_approval import approve_discovery_run


class ApprovedExecutionTests(unittest.TestCase):

    def _make_approved_run(self, root):
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("x = 1\n")

        run_dir = root / "runs" / "run-1"
        run_dir.mkdir(parents=True)

        (run_dir / "task.json").write_text(json.dumps({
            "task_id": "EXEC-001",
            "instruction": "Repair app.",
            "verification_command": "true",
        }))

        (run_dir / "discovery.json").write_text(json.dumps({
            "candidate_files": ["src/app.py"],
            "selected_targets": ["src/app.py"],
            "status": "targets_selected",
        }))

        (run_dir / "run.json").write_text(json.dumps({
            "run_id": "run-1",
            "task_id": "EXEC-001",
            "status": "targets_selected",
        }))

        approve_discovery_run(root, run_dir, ["src/app.py"])
        return run_dir

    def test_executes_after_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = self._make_approved_run(root)

            fake_result = type("Result", (), {
                "task_id": "EXEC-001",
                "passed": True,
                "attempts": 1,
                "final_verification_output": "PASS",
                "rolled_back": False,
                "audit": [{"event": "repair_attempt"}],
            })()

            with patch("approved_execution.TaskExecutor") as executor_cls:
                executor_cls.return_value.execute.return_value = fake_result

                report = execute_approved_run(
                    root,
                    run_dir,
                    object(),
                    model_name="test-model",
                )

            self.assertTrue(report.passed)

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(manifest["status"], "passed")

    def test_rejects_execution_before_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x = 1\n")

            run_dir = root / "runs" / "run-1"
            run_dir.mkdir(parents=True)

            (run_dir / "task.json").write_text(json.dumps({
                "task_id": "EXEC-002",
                "instruction": "Repair app.",
                "verification_command": "true",
            }))

            (run_dir / "run.json").write_text(json.dumps({
                "run_id": "run-1",
                "task_id": "EXEC-002",
                "status": "targets_selected",
            }))

            with self.assertRaises(FileNotFoundError):
                execute_approved_run(
                    root,
                    run_dir,
                    object(),
                    model_name="test-model",
                )


if __name__ == "__main__":
    unittest.main()
