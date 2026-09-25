import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from approved_execution import execute_approved_run
from target_approval import approve_discovery_run
from task_runner import run_task


class ApprovedFlowE2ETests(unittest.TestCase):

    def test_discovery_to_approval_to_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()

            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text(
                "x = 1\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "E2E-001",
                        "instruction": "Repair app.",
                        "verification_command": "true",
                    }
                )
            )

            runs_root = repo / "runs"

            discovery_report = run_task(
                repo,
                task_file,
                Path("models/granite-4.0-1b-Q4_K_M.gguf"),
                runs_root=runs_root,
            )

            self.assertEqual(
                discovery_report.status,
                "targets_selected",
            )
            self.assertEqual(
                discovery_report.selected_targets,
                ["src/app.py"],
            )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            approve_discovery_run(
                repo,
                run_dir,
                ["src/app.py"],
            )

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                manifest["status"],
                "approved",
            )

            fake_result = type(
                "Result",
                (),
                {
                    "task_id": "E2E-001",
                    "passed": True,
                    "attempts": 1,
                    "final_verification_output": "PASS",
                    "rolled_back": False,
                    "audit": [
                        {
                            "event": "repair_attempt",
                            "attempt": 1,
                        }
                    ],
                },
            )()

            with patch(
                "approved_execution.TaskExecutor"
            ) as executor_cls:
                executor_cls.return_value.execute.return_value = (
                    fake_result
                )

                report = execute_approved_run(
                    repo,
                    run_dir,
                    object(),
                    model_name="test-model",
                )

            self.assertTrue(report.passed)
            self.assertEqual(
                report.targets,
                ["src/app.py"],
            )

            final_manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                final_manifest["status"],
                "passed",
            )


if __name__ == "__main__":
    unittest.main()
