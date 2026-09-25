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
from model_interface import FixSimpleModel, ModelResponse
from remote_openai_model import RemoteOpenAIModel
from target_approval import approve_discovery_run
from task_runner import run_task


REMOTE_MODEL = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"


class FirstAttemptFailsThenQwen(FixSimpleModel):
    def __init__(self, qwen):
        self.qwen = qwen
        self.calls = []

    def complete(self, request):
        self.calls.append(request)

        if len(self.calls) == 1:
            return ModelResponse(
                content=(
                    "def subtract(a, b):\n"
                    "    return 10\n"
                ),
                model="controlled-first-failure",
            )

        return self.qwen.complete(request)


@unittest.skipUnless(
    os.environ.get("FIXSIMPLE_MODEL_BASE_URL"),
    "FIXSIMPLE_MODEL_BASE_URL not set",
)
class QwenRetryRecoveryE2ETests(unittest.TestCase):

    def test_second_attempt_uses_verification_feedback_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            (repo / "src").mkdir()
            (repo / "tests").mkdir()

            target = repo / "src" / "math_ops.py"
            target.write_text(
                "def subtract(a, b):\n"
                "    return a + b\n"
            )

            verify = repo / "tests" / "verify_math_ops.py"
            verify.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from math_ops import subtract\n"
                "actual = subtract(10, 3)\n"
                "if actual != 7:\n"
                "    print(f'expected subtract(10, 3) == 7, got {actual}', file=sys.stderr)\n"
                "    raise SystemExit(1)\n"
                "print('V0.44 retry recovery PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.44-RETRY-E2E-001",
                        "instruction": (
                            "Fix subtract so subtract(10, 3) returns 7. "
                            "Select only the source file that defines subtract."
                        ),
                        "verification_command": (
                            "python3 tests/verify_math_ops.py"
                        ),
                        "max_repair_iterations": 2,
                        "protected_paths": [
                            "tests",
                            "task.json",
                        ],
                    }
                )
            )

            qwen = RemoteOpenAIModel(
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
                selection_model=qwen,
            )

            self.assertEqual(
                discovery.selected_targets,
                ["src/math_ops.py"],
            )

            run_dir = next(runs_root.iterdir())

            approve_discovery_run(
                repo,
                run_dir,
                discovery.selected_targets,
            )

            recovery_model = FirstAttemptFailsThenQwen(qwen)

            report = execute_approved_run(
                repo,
                run_dir,
                recovery_model,
                model_name=REMOTE_MODEL,
            )

            self.assertTrue(report.passed)
            self.assertEqual(report.attempts, 2)
            self.assertEqual(len(recovery_model.calls), 2)

            second_request = recovery_model.calls[1]
            self.assertIn(
                "VERIFICATION FAILURE:",
                second_request.context,
            )
            self.assertIn(
                "got 10",
                second_request.context,
            )
            self.assertIn(
                "return a + b",
                second_request.context,
            )
            self.assertNotIn(
                "return 10",
                second_request.context,
            )

            self.assertIn(
                "return a - b",
                target.read_text(),
            )
            self.assertIn(
                "V0.44 retry recovery PASS",
                report.verification_output,
            )

            repair_events = [
                event
                for event in report.audit
                if event.get("event") == "repair_attempt"
            ]

            self.assertEqual(len(repair_events), 2)
            self.assertFalse(
                repair_events[0]["verification_passed"],
            )
            self.assertTrue(
                repair_events[1]["verification_passed"],
            )
            self.assertIn(
                "got 10",
                repair_events[0]["verification_output"],
            )

            final_manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                final_manifest["status"],
                "passed",
            )
            self.assertEqual(
                final_manifest["approved_targets"],
                ["src/math_ops.py"],
            )


if __name__ == "__main__":
    unittest.main()
