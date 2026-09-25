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


if __name__ == "__main__":
    unittest.main()
