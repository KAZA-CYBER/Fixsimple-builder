import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from model_interface import (
    FixSimpleModel,
    ModelRequest,
    ModelResponse,
)
from task_contract import BuilderTask
from task_executor import TaskExecutor


class RepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content="def add(a, b):\n    return a + b\n",
            model="fake-repair-model",
        )


class MultiFileRepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        if request.response_contract != "multi_file_json":
            raise AssertionError(
                "expected multi_file_json response contract"
            )

        return ModelResponse(
            content=json.dumps(
                {
                    "files": {
                        "a.py": (
                            "def add(a, b):\n"
                            "    return a + b\n"
                        ),
                        "b.py": (
                            "def multiply(a, b):\n"
                            "    return a * b\n"
                        ),
                    }
                }
            ),
            model="fake-multi-file-model",
        )


class InvalidMultiFileRepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content=json.dumps(
                {
                    "files": {
                        "a.py": "x = 1\n",
                        "extra.py": "x = 2\n",
                    }
                }
            ),
            model="fake-invalid-multi-file-model",
        )


class TaskExecutorTests(unittest.TestCase):

    def test_general_repair_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text(
                "def add(a, b):\n    return a - b\n"
            )

            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
                "print('PASS')\n"
            )

            task = BuilderTask(
                task_id="V0.2-TEST-001",
                instruction=(
                    "Repair target.py so verify.py passes."
                ),
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=2,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=RepairModel(),
            )

            result = executor.execute(task)

            self.assertTrue(result.passed)
            self.assertEqual(result.attempts, 1)
            self.assertIn(
                "return a + b",
                (root / "target.py").read_text(),
            )
            self.assertIn(
                "PASS",
                result.final_verification_output,
            )


    def test_multi_file_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "a.py").write_text(
                "def add(a, b):\n"
                "    return a - b\n"
            )

            (root / "b.py").write_text(
                "def multiply(a, b):\n"
                "    return a + b\n"
            )

            (root / "verify.py").write_text(
                "from a import add\n"
                "from b import multiply\n"
                "assert add(2, 3) == 5\n"
                "assert multiply(2, 3) == 6\n"
                "print('PASS')\n"
            )

            task = BuilderTask(
                task_id="V0.13-MULTI-001",
                instruction="Repair both target files.",
                target_files=["a.py", "b.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=2,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=MultiFileRepairModel(),
            )

            result = executor.execute(task)

            self.assertTrue(result.passed)
            self.assertEqual(result.attempts, 1)
            self.assertIn(
                "return a + b",
                (root / "a.py").read_text(),
            )
            self.assertIn(
                "return a * b",
                (root / "b.py").read_text(),
            )

    def test_multi_file_rejects_target_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "a.py").write_text("x = 0\n")
            (root / "b.py").write_text("y = 0\n")
            (root / "verify.py").write_text(
                "raise SystemExit(1)\n"
            )

            task = BuilderTask(
                task_id="V0.13-MULTI-002",
                instruction="Repair both target files.",
                target_files=["a.py", "b.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=InvalidMultiFileRepairModel(),
            )

            with self.assertRaisesRegex(
                ValueError,
                "multi-file response target mismatch",
            ):
                executor.execute(task)


if __name__ == "__main__":
    unittest.main()
