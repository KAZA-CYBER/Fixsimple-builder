import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from task_runner import run_task


class RunArtifactTests(unittest.TestCase):

    def test_run_creates_task_report_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text("x = 1\n")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.16-RUN-001",
                        "instruction": "Keep target valid.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            runs_root = root / "runs"
            (root / "fake.gguf").write_bytes(b"")

            with patch("task_runner.LocalLlamaModel"):
                report = run_task(
                    repo_root=root,
                    task_file=task_file,
                    model_path=root / "fake.gguf",
                    backend="local",
                    runs_root=runs_root,
                )

            self.assertTrue(report.passed)

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)

            run_dir = run_dirs[0]

            self.assertTrue((run_dir / "task.json").exists())
            self.assertTrue((run_dir / "report.json").exists())
            self.assertTrue((run_dir / "audit.json").exists())
            self.assertTrue((run_dir / "run.json").exists())

    def test_run_exception_creates_error_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text("x = 1\n")
            (root / "fake.gguf").write_bytes(b"")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.17-ERROR-001",
                        "instruction": "Trigger executor failure.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            runs_root = root / "runs"

            with patch("task_runner.LocalLlamaModel"), patch(
                "task_runner.TaskExecutor.execute",
                side_effect=RuntimeError("forced failure"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "forced failure",
                ):
                    run_task(
                        repo_root=root,
                        task_file=task_file,
                        model_path=root / "fake.gguf",
                        backend="local",
                        runs_root=runs_root,
                    )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)

            run_dir = run_dirs[0]

            self.assertTrue((run_dir / "task.json").exists())
            self.assertTrue((run_dir / "error.json").exists())
            self.assertTrue((run_dir / "audit.json").exists())
            self.assertTrue((run_dir / "run.json").exists())

            error = json.loads(
                (run_dir / "error.json").read_text()
            )

            self.assertEqual(
                error["event"],
                "runtime_exception",
            )
            self.assertEqual(
                error["exception_type"],
                "RuntimeError",
            )
            self.assertEqual(
                error["message"],
                "forced failure",
            )

    def test_run_failed_writes_failed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text("x = 1\n")
            (root / "fake.gguf").write_bytes(b"")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.18-FAILED-001",
                        "instruction": "Keep failing verification.",
                        "target_files": ["target.py"],
                        "verification_command": "false",
                        "max_repair_iterations": 1,
                    }
                )
            )

            runs_root = root / "runs"

            failed_result = type(
                "Result",
                (),
                {
                    "task_id": "V0.18-FAILED-001",
                    "passed": False,
                    "attempts": 1,
                    "final_verification_output": "verification failed",
                    "rolled_back": True,
                    "audit": [],
                },
            )()

            with patch("task_runner.LocalLlamaModel"), patch(
                "task_runner.TaskExecutor.execute",
                return_value=failed_result,
            ):
                report = run_task(
                    repo_root=root,
                    task_file=task_file,
                    model_path=root / "fake.gguf",
                    backend="local",
                    runs_root=runs_root,
                )

            self.assertFalse(report.passed)

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)

            manifest = json.loads(
                (run_dirs[0] / "run.json").read_text()
            )

            self.assertEqual(
                manifest["status"],
                "failed",
            )
            self.assertEqual(
                manifest["task_id"],
                "V0.18-FAILED-001",
            )
            self.assertIn("started_at", manifest)
            self.assertIn("finished_at", manifest)
            self.assertGreaterEqual(
                manifest["finished_at"],
                manifest["started_at"],
            )

    def test_run_writes_running_manifest_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text("x = 1\n")
            (root / "fake.gguf").write_bytes(b"")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.20-RUNNING-001",
                        "instruction": "Observe running manifest.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            runs_root = root / "runs"

            def inspect_running(*args, **kwargs):
                run_dirs = list(runs_root.iterdir())
                self.assertEqual(len(run_dirs), 1)

                manifest = json.loads(
                    (run_dirs[0] / "run.json").read_text()
                )

                self.assertEqual(
                    manifest["status"],
                    "running",
                )
                self.assertIsNone(
                    manifest["finished_at"],
                )
                self.assertIsInstance(
                    manifest["pid"],
                    int,
                )
                self.assertGreater(
                    manifest["pid"],
                    0,
                )

                return type(
                    "Result",
                    (),
                    {
                        "task_id": "V0.20-RUNNING-001",
                        "passed": True,
                        "attempts": 0,
                        "final_verification_output": "PASS",
                        "rolled_back": False,
                        "audit": [],
                    },
                )()

            with patch("task_runner.LocalLlamaModel"), patch(
                "task_runner.TaskExecutor.execute",
                side_effect=inspect_running,
            ):
                report = run_task(
                    repo_root=root,
                    task_file=task_file,
                    model_path=root / "fake.gguf",
                    backend="local",
                    runs_root=runs_root,
                )

            self.assertTrue(report.passed)

if __name__ == "__main__":
    unittest.main()
