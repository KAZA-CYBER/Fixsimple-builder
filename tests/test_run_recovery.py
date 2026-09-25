import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from run_recovery import mark_stale_runs


class RunRecoveryTests(unittest.TestCase):

    def test_marks_stale_running_run_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"
            run_dir = runs_root / "run-1"
            run_dir.mkdir(parents=True)

            started_at = (
                datetime.now(timezone.utc)
                - timedelta(hours=1)
            ).isoformat()

            (run_dir / "run.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "task_id": "TASK-1",
                        "status": "running",
                        "started_at": started_at,
                        "finished_at": None,
                    }
                )
            )

            interrupted = mark_stale_runs(
                runs_root,
                stale_after_seconds=60,
            )

            self.assertEqual(interrupted, ["run-1"])

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )

            self.assertEqual(
                manifest["status"],
                "interrupted",
            )
            self.assertIsNotNone(
                manifest["finished_at"],
            )

    def test_leaves_completed_run_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"
            run_dir = runs_root / "run-2"
            run_dir.mkdir(parents=True)

            manifest = {
                "run_id": "run-2",
                "task_id": "TASK-2",
                "status": "passed",
                "started_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "finished_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            (run_dir / "run.json").write_text(
                json.dumps(manifest)
            )

            interrupted = mark_stale_runs(
                runs_root,
                stale_after_seconds=0,
            )

            self.assertEqual(interrupted, [])

            unchanged = json.loads(
                (run_dir / "run.json").read_text()
            )

            self.assertEqual(
                unchanged["status"],
                "passed",
            )

    def test_leaves_fresh_running_run_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"
            run_dir = runs_root / "run-3"
            run_dir.mkdir(parents=True)

            (run_dir / "run.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-3",
                        "task_id": "TASK-3",
                        "status": "running",
                        "started_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "finished_at": None,
                    }
                )
            )

            interrupted = mark_stale_runs(
                runs_root,
                stale_after_seconds=3600,
            )

            self.assertEqual(interrupted, [])

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )

            self.assertEqual(
                manifest["status"],
                "running",
            )


if __name__ == "__main__":
    unittest.main()
