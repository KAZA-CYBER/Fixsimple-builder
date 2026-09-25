import json
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
from target_approval import approve_discovery_run
from task_runner import run_task


class SelectionModel(FixSimpleModel):
    def complete(self, request):
        self.last_request = request
        return ModelResponse(
            content='{"targets":["src/math_utils.py"]}',
            model="selection-model",
        )


class RepairModel(FixSimpleModel):
    def complete(self, request):
        self.last_request = request
        return ModelResponse(
            content=(
                "def subtract(a, b):\n"
                "    return a - b\n"
            ),
            model="repair-model",
        )


class RealEngineeringE2ETests(unittest.TestCase):

    def test_task_without_targets_repairs_real_file(self):
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
                "print('V0.40 verification PASS')\n"
            )

            task_file = repo / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "V0.40-REAL-E2E-001",
                        "instruction": (
                            "Fix subtract so it returns the "
                            "difference between two numbers."
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

            runs_root = repo / "runs"

            discovery = run_task(
                repo_root=repo,
                task_file=task_file,
                model_path=repo / "unused.gguf",
                backend="local",
                runs_root=runs_root,
                selection_model=SelectionModel(),
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
                ["src/math_utils.py"],
            )

            run_dirs = list(runs_root.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            approve_discovery_run(
                repo,
                run_dir,
                discovery.selected_targets,
            )

            manifest = json.loads(
                (run_dir / "run.json").read_text()
            )
            self.assertEqual(
                manifest["status"],
                "approved",
            )

            report = execute_approved_run(
                repo,
                run_dir,
                RepairModel(),
                model_name="repair-model",
            )

            self.assertTrue(report.passed)
            self.assertEqual(report.attempts, 1)
            self.assertEqual(
                report.targets,
                ["src/math_utils.py"],
            )
            self.assertIn(
                "V0.40 verification PASS",
                report.verification_output,
            )

            self.assertEqual(
                target.read_text(),
                (
                    "def subtract(a, b):\n"
                    "    return a - b\n"
                ),
            )

            audit = json.loads(
                (run_dir / "audit.json").read_text()
            )
            events = [
                item["event"]
                for item in audit
            ]

            self.assertIn(
                "targets_approved",
                events,
            )
            self.assertIn(
                "initial_verification",
                events,
            )
            self.assertIn(
                "repair_attempt",
                events,
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
