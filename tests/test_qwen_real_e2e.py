import json
import os
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from approved_execution import execute_approved_run
from remote_openai_model import RemoteOpenAIModel
from target_approval import approve_discovery_run
from task_runner import run_task


REMOTE_MODEL = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"


@unittest.skipUnless(
    os.environ.get("FIXSIMPLE_MODEL_BASE_URL"),
    "FIXSIMPLE_MODEL_BASE_URL not set",
)
class QwenRealE2ETests(unittest.TestCase):

    def test_qwen_selects_and_repairs_real_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            (repo / "src").mkdir()
            (repo / "tests").mkdir()

            target = repo / "src" / "math_utils.py"
            target.write_text(
                "def subtract(a, b):\n"
                "    return a + b\n"
            )

            verify = repo / "tests" / "verify_math.py"
            verify.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from math_utils import subtract\n"
                "assert subtract(10, 3) == 7\n"
                "print('V0.41 Qwen verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.41-QWEN-E2E-001",
                        "instruction": (
                            "Fix the subtract implementation so "
                            "subtract(10, 3) returns 7. Select the "
                            "implementation source file that defines "
                            "subtract; do not select tests."
                        ),
                        "verification_command": (
                            "python3 tests/verify_math.py"
                        ),
                        "max_repair_iterations": 2,
                        "protected_paths": [
                            "tests",
                            "task.json",
                        ],
                    }
                )
            )

            model = RemoteOpenAIModel(
                base_url=os.environ[
                    "FIXSIMPLE_MODEL_BASE_URL"
                ],
                model=REMOTE_MODEL,
            )

            runs_root = repo / "runs"

            discovery = run_task(
                repo_root=repo,
                task_file=task_file,
                model_path=repo / "unused.gguf",
                backend="remote",
                base_url=os.environ[
                    "FIXSIMPLE_MODEL_BASE_URL"
                ],
                remote_model=REMOTE_MODEL,
                runs_root=runs_root,
                selection_model=model,
            )

            self.assertEqual(
                discovery.status,
                "targets_selected",
            )
            self.assertEqual(
                discovery.selection_source,
                "model",
            )
            self.assertIn(
                "src/math_utils.py",
                discovery.selected_targets,
            )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            approve_discovery_run(
                repo,
                run_dir,
                ["src/math_utils.py"],
            )

            approved_manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                approved_manifest["status"],
                "approved",
            )

            report = execute_approved_run(
                repo,
                run_dir,
                model,
                model_name=REMOTE_MODEL,
            )

            self.assertTrue(report.passed)
            self.assertGreaterEqual(report.attempts, 1)
            self.assertEqual(
                report.targets,
                ["src/math_utils.py"],
            )
            self.assertIn(
                "V0.41 Qwen verification PASS",
                report.verification_output,
            )
            self.assertIn(
                "return a - b",
                target.read_text(),
            )

            final_manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                final_manifest["status"],
                "passed",
            )
            self.assertEqual(
                final_manifest["model"],
                REMOTE_MODEL,
            )


if __name__ == "__main__":
    unittest.main()
