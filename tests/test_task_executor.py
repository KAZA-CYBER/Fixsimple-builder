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


class FailingRepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content="def add(a, b):\n    return 999\n",
            model="fake-failing-model",
        )


class PartiallyInvalidMultiFileModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content=json.dumps(
                {
                    "files": {
                        "a.py": "x = 1\n",
                        "b.py": 123,
                    }
                }
            ),
            model="fake-partially-invalid-model",
        )




class SandboxFailingRepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content="def add(a, b):\n    return 999\n",
            model="sandbox-failing-model",
        )


class SandboxPassingRepairModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content="def add(a, b):\n    return a + b\n",
            model="sandbox-passing-model",
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


    def test_final_failure_restores_original_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            original = (
                "def add(a, b):\n"
                "    return a - b\n"
            )

            (root / "target.py").write_text(original)

            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
            )

            task = BuilderTask(
                task_id="V0.14-ROLLBACK-001",
                instruction="Repair target.py.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=2,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=FailingRepairModel(),
            )

            result = executor.execute(task)

            self.assertFalse(result.passed)
            self.assertEqual(result.attempts, 2)
            self.assertEqual(
                (root / "target.py").read_text(),
                original,
            )

    def test_exception_restores_original_multi_file_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            original_a = "x = 0\n"
            original_b = "y = 0\n"

            (root / "a.py").write_text(original_a)
            (root / "b.py").write_text(original_b)

            (root / "verify.py").write_text(
                "raise SystemExit(1)\n"
            )

            task = BuilderTask(
                task_id="V0.14-ROLLBACK-002",
                instruction="Repair both files.",
                target_files=["a.py", "b.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=PartiallyInvalidMultiFileModel(),
            )

            with self.assertRaisesRegex(
                ValueError,
                "multi-file response content must be text",
            ):
                executor.execute(task)

            self.assertEqual(
                (root / "a.py").read_text(),
                original_a,
            )
            self.assertEqual(
                (root / "b.py").read_text(),
                original_b,
            )


    def test_audit_records_successful_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text(
                "def add(a, b):\n"
                "    return a - b\n"
            )

            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
                "print('PASS')\n"
            )

            task = BuilderTask(
                task_id="V0.15-AUDIT-001",
                instruction="Repair target.py.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=2,
            )

            result = TaskExecutor(
                repo_root=root,
                model=RepairModel(),
            ).execute(task)

            self.assertTrue(result.passed)
            self.assertFalse(result.rolled_back)

            self.assertEqual(
                [event["event"] for event in result.audit],
                [
                    "initial_verification",
                    "repair_attempt",
                ],
            )

            self.assertFalse(
                result.audit[0]["passed"],
            )
            self.assertTrue(
                result.audit[1]["verification_passed"],
            )
            self.assertEqual(
                result.audit[1]["attempt"],
                1,
            )

    def test_audit_records_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text(
                "def add(a, b):\n"
                "    return a - b\n"
            )

            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
            )

            task = BuilderTask(
                task_id="V0.15-AUDIT-002",
                instruction="Repair target.py.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            result = TaskExecutor(
                repo_root=root,
                model=FailingRepairModel(),
            ).execute(task)

            self.assertFalse(result.passed)
            self.assertTrue(result.rolled_back)

            self.assertEqual(
                [event["event"] for event in result.audit],
                [
                    "initial_verification",
                    "repair_attempt",
                    "rollback",
                ],
            )

            self.assertEqual(
                result.audit[-1]["reason"],
                "repair_iterations_exhausted",
            )


    def test_failed_sandbox_verification_does_not_touch_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = "def add(a, b):\n    return a - b\n"

            (root / "target.py").write_text(original)
            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
            )

            task = BuilderTask(
                task_id="V0.52-SANDBOX-001",
                instruction="Repair target.py.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            result = TaskExecutor(
                repo_root=root,
                model=SandboxFailingRepairModel(),
            ).execute(task)

            self.assertFalse(result.passed)
            self.assertEqual(
                (root / "target.py").read_text(),
                original,
            )
            self.assertFalse(
                result.audit[1]["sandbox_verification_passed"],
            )

    def test_passing_sandbox_verification_commits_to_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "target.py").write_text(
                "def add(a, b):\n    return a - b\n"
            )
            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
            )

            task = BuilderTask(
                task_id="V0.52-SANDBOX-002",
                instruction="Repair target.py.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            result = TaskExecutor(
                repo_root=root,
                model=SandboxPassingRepairModel(),
            ).execute(task)

            self.assertTrue(result.passed)
            self.assertTrue(
                result.audit[1]["sandbox_verification_passed"],
            )
            self.assertIn(
                "return a + b",
                (root / "target.py").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
