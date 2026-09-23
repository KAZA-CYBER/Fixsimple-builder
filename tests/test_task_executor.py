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


if __name__ == "__main__":
    unittest.main()
