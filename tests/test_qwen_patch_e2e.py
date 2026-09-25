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
class QwenPatchE2ETests(unittest.TestCase):

    def test_qwen_repairs_single_file_with_patch_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "tests").mkdir()

            target = repo / "src" / "math_utils.py"
            target.write_text(
                "def subtract(a, b):\n"
                "    return a + b\n"
            )

            (repo / "tests" / "verify_math.py").write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from math_utils import subtract\n"
                "assert subtract(10, 3) == 7\n"
                "print('V0.48 patch verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.48-QWEN-PATCH-001",
                        "instruction": (
                            "Fix subtract so it returns the difference. "
                            "Select only the implementation source file."
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
                discovery.selected_targets,
                ["src/math_utils.py"],
            )

            run_dir = next(runs_root.iterdir())
            approve_discovery_run(
                repo,
                run_dir,
                discovery.selected_targets,
            )

            report = execute_approved_run(
                repo,
                run_dir,
                model,
                model_name=REMOTE_MODEL,
            )

            self.assertTrue(report.passed)
            self.assertIn(
                "return a - b",
                target.read_text(),
            )

            repair_events = [
                event
                for event in report.audit
                if event.get("event") == "repair_attempt"
            ]
            self.assertTrue(repair_events)
            self.assertEqual(
                repair_events[-1]["response_contract"],
                "patch_json",
            )


if __name__ == "__main__":
    unittest.main()
