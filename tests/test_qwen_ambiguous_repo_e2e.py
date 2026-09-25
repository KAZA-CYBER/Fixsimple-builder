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
class QwenAmbiguousRepoE2ETests(unittest.TestCase):

    def test_qwen_selects_exact_implementation_among_similar_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            (repo / "src").mkdir()
            (repo / "tests").mkdir()

            pricing = repo / "src" / "pricing.py"
            pricing.write_text(
                "def calculate_total(subtotal, tax):\n"
                "    return subtotal - tax\n"
            )

            (repo / "src" / "order_service.py").write_text(
                "from pricing import calculate_total\n\n"
                "def checkout_total(subtotal, tax):\n"
                "    return calculate_total(subtotal, tax)\n"
            )

            (repo / "src" / "tax.py").write_text(
                "def calculate_tax(subtotal, rate):\n"
                "    return subtotal * rate\n"
            )

            (repo / "src" / "invoice.py").write_text(
                "from pricing import calculate_total\n\n"
                "def invoice_amount(subtotal, tax):\n"
                "    return calculate_total(subtotal, tax)\n"
            )

            (repo / "src" / "discount.py").write_text(
                "def calculate_discount(subtotal, rate):\n"
                "    return subtotal * rate\n"
            )

            verify = repo / "tests" / "verify_pricing.py"
            verify.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
                "from pricing import calculate_total\n"
                "assert calculate_total(100, 15) == 115\n"
                "print('V0.42 ambiguous repo verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.42-AMBIGUOUS-E2E-001",
                        "instruction": (
                            "Fix the implementation of calculate_total so "
                            "a subtotal of 100 plus tax of 15 returns 115. "
                            "Choose only the source file that actually "
                            "defines calculate_total. Do not select callers, "
                            "tests, tax helpers, invoice code, or discount "
                            "helpers."
                        ),
                        "verification_command": (
                            "python3 tests/verify_pricing.py"
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
                discovery.selected_targets,
                ["src/pricing.py"],
            )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            repo_map = json.loads(
                (run_dir / "repository_map.json").read_text()
            )

            self.assertIn(
                "calculate_total",
                repo_map["src/pricing.py"]["definitions"],
            )
            self.assertIn(
                "calculate_total",
                repo_map["src/order_service.py"]["references"],
            )

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
                report.targets,
                ["src/pricing.py"],
            )
            self.assertIn(
                "V0.42 ambiguous repo verification PASS",
                report.verification_output,
            )
            self.assertIn(
                "return subtotal + tax",
                pricing.read_text(),
            )

            self.assertIn(
                "return calculate_total(subtotal, tax)",
                (repo / "src" / "order_service.py").read_text(),
            )
            self.assertIn(
                "return subtotal * rate",
                (repo / "src" / "tax.py").read_text(),
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
