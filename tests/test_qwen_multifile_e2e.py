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
class QwenMultiFileE2ETests(unittest.TestCase):

    def test_qwen_selects_and_repairs_two_required_files(self):
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

            (repo / "src" / "tax_rules.py").write_text(
                "def normalize_tax(tax):\n"
                "    return tax\n"
            )

            verify = repo / "tests" / "verify_receipt.py"
            verify.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from order_service import build_receipt\n"
                "assert build_receipt(100, 15) == 'Total: $115'\n"
                "print('V0.43 multi-file verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.43-MULTIFILE-E2E-001",
                        "instruction": (
                            "Fix receipt generation so build_receipt(100, 15) "
                            "returns exactly 'Total: $115'. The arithmetic "
                            "implementation and the total formatting are both "
                            "wrong and both source files must be corrected. "
                            "Select exactly the two implementation files that "
                            "define add_tax and format_total. Do not select the "
                            "caller, tests, or unrelated helpers."
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
                discovery.status,
                "targets_selected",
            )
            self.assertEqual(
                discovery.selection_source,
                "model",
            )
            self.assertEqual(
                set(discovery.selected_targets),
                {
                    "src/pricing.py",
                    "src/receipt.py",
                },
            )
            self.assertEqual(
                len(discovery.selected_targets),
                2,
            )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

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
            self.assertEqual(
                set(report.targets),
                {
                    "src/pricing.py",
                    "src/receipt.py",
                },
            )
            self.assertIn(
                "V0.43 multi-file verification PASS",
                report.verification_output,
            )
            self.assertIn(
                "return subtotal + tax",
                pricing.read_text(),
            )
            self.assertIn(
                "Total: $",
                receipt.read_text(),
            )

            self.assertIn(
                "return format_total(add_tax(subtotal, tax))",
                (repo / "src" / "order_service.py").read_text(),
            )
            self.assertIn(
                "return tax",
                (repo / "src" / "tax_rules.py").read_text(),
            )

            audit = json.loads(
                (run_dir / "audit.json").read_text()
            )
            repair_events = [
                item
                for item in audit
                if item.get("event") == "repair_attempt"
            ]
            self.assertTrue(repair_events)
            self.assertEqual(
                repair_events[-1]["response_contract"],
                "multi_patch_json",
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
