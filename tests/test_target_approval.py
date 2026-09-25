import json
import tempfile
import unittest
from pathlib import Path

from target_approval import (
    approve_discovery_run,
    build_approved_task,
)


class TargetApprovalTests(unittest.TestCase):
    def _make_run(self, root: Path):
        repo = root / "repo"
        repo.mkdir()
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("print('x')\n")
        (repo / "src" / "other.py").write_text("print('y')\n")

        run_dir = root / "run"
        run_dir.mkdir()

        (run_dir / "task.json").write_text(
            json.dumps(
                {
                    "task_id": "APPROVAL-001",
                    "instruction": "Repair app.",
                    "verification_command": "true",
                    "protected_paths": [],
                }
            )
        )

        (run_dir / "discovery.json").write_text(
            json.dumps(
                {
                    "candidate_files": [
                        "src/app.py",
                        "src/other.py",
                    ],
                    "selected_targets": [
                        "src/app.py",
                    ],
                    "status": "targets_selected",
                }
            )
        )

        (run_dir / "run.json").write_text(
            json.dumps(
                {
                    "run_id": "run-1",
                    "task_id": "APPROVAL-001",
                    "status": "targets_selected",
                }
            )
        )

        return repo, run_dir

    def test_can_approve_selected_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, run_dir = self._make_run(Path(tmp))

            approval = approve_discovery_run(
                repo,
                run_dir,
                ["src/app.py"],
            )

            self.assertEqual(
                approval["approved_targets"],
                ["src/app.py"],
            )

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                manifest["status"],
                "approved",
            )

    def test_can_approve_different_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, run_dir = self._make_run(Path(tmp))

            approval = approve_discovery_run(
                repo,
                run_dir,
                ["src/other.py"],
            )

            self.assertEqual(
                approval["approved_targets"],
                ["src/other.py"],
            )

    def test_rejects_non_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, run_dir = self._make_run(Path(tmp))

            with self.assertRaises(ValueError):
                approve_discovery_run(
                    repo,
                    run_dir,
                    ["README.md"],
                )

    def test_rejects_non_approvable_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, run_dir = self._make_run(Path(tmp))

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            manifest["status"] = "passed"
            (run_dir / "run.json").write_text(
                json.dumps(manifest)
            )

            with self.assertRaises(ValueError):
                approve_discovery_run(
                    repo,
                    run_dir,
                    ["src/app.py"],
                )

    def test_build_approved_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, run_dir = self._make_run(Path(tmp))

            approve_discovery_run(
                repo,
                run_dir,
                ["src/app.py"],
            )

            task = build_approved_task(
                repo,
                run_dir,
            )

            self.assertEqual(
                task.target_files,
                ["src/app.py"],
            )


if __name__ == "__main__":
    unittest.main()
