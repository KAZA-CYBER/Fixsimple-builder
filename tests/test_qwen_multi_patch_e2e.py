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
class QwenMultiPatchE2ETests(unittest.TestCase):

    def test_qwen_repairs_two_files_with_multi_patch_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "tests").mkdir()

            pricing = repo / "src" / "pricing.py"
            pricing.write_text(
                "def add_tax(subtotal, tax):\n"
                "    return subtotal - tax\n"
            )

            receipt = repo / "src" / "receipt.py"
            receipt.write_text(
                "def format_total(total):\n"
                "    return f'Total={total}'\n"
            )

            (repo / "src" / "order_service.py").write_text(
                "from pricing import add_tax\n"
                "from receipt import format_total\n\n"
                "def build_receipt(subtotal, tax):\n"
                "    return format_total(add_tax(subtotal, tax))\n"
            )

            (repo / "tests" / "verify_receipt.py").write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from order_service import build_receipt\n"
                "assert build_receipt(100, 15) == 'Total: $115'\n"
                "print('V0.49 multi-patch verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.49-QWEN-MULTIPATCH-001",
                        "instruction": (
                            "Fix receipt generation so build_receipt(100, 15) "
                            "returns exactly 'Total: $115'. The arithmetic "
                            "and formatting implementations are both wrong. "
                            "Select exactly the two implementation source "
                            "files that define add_tax and format_total."
                        ),
                        "verification_command": (
                            "python3 tests/verify_receipt.py"
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
                set(discovery.selected_targets),
                {"src/pricing.py", "src/receipt.py"},
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
                "return subtotal + tax",
                pricing.read_text(),
            )
            self.assertIn(
                "Total: $",
                receipt.read_text(),
            )

            repair_events = [
                event
                for event in report.audit
                if event.get("event") == "repair_attempt"
            ]
            self.assertTrue(repair_events)
            self.assertEqual(
                repair_events[-1]["response_contract"],
                "multi_patch_json",
            )


if __name__ == "__main__":
    unittest.main()
