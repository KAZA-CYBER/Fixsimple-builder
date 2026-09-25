import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import FixSimpleModel, ModelResponse
from patch_edit import apply_exact_patch, parse_patch_response
from task_contract import BuilderTask
from task_executor import TaskExecutor


class PatchModel(FixSimpleModel):
    supports_patch_edits = True

    def complete(self, request):
        self.last_request = request
        return ModelResponse(
            content=json.dumps(
                {
                    "patch": {
                        "path": "target.py",
                        "old": "return a - b",
                        "new": "return a + b",
                    }
                }
            ),
            model="patch-model",
        )


class PatchEditingTests(unittest.TestCase):

    def test_parse_and_apply_exact_patch(self):
        path, old, new = parse_patch_response(
            json.dumps(
                {
                    "patch": {
                        "path": "target.py",
                        "old": "x = 1",
                        "new": "x = 2",
                    }
                }
            ),
            expected_target="target.py",
        )

        self.assertEqual(path, "target.py")
        self.assertEqual(
            apply_exact_patch(
                "x = 1\ny = 3\n",
                old=old,
                new=new,
            ),
            "x = 2\ny = 3\n",
        )

    def test_rejects_wrong_target(self):
        with self.assertRaisesRegex(
            ValueError,
            "patch target mismatch",
        ):
            parse_patch_response(
                json.dumps(
                    {
                        "patch": {
                            "path": "other.py",
                            "old": "x",
                            "new": "y",
                        }
                    }
                ),
                expected_target="target.py",
            )

    def test_rejects_ambiguous_old_text(self):
        with self.assertRaisesRegex(
            ValueError,
            "match exactly once",
        ):
            apply_exact_patch(
                "x = 1\nx = 1\n",
                old="x = 1",
                new="x = 2",
            )

    def test_executor_uses_patch_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            target = root / "target.py"
            target.write_text(
                "def add(a, b):\n"
                "    return a - b\n"
            )
            (root / "verify.py").write_text(
                "from target import add\n"
                "assert add(2, 3) == 5\n"
                "print('PASS')\n"
            )

            model = PatchModel()
            task = BuilderTask(
                task_id="V0.48-PATCH-001",
                instruction="Fix add.",
                target_files=["target.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            result = TaskExecutor(root, model).execute(task)

            self.assertTrue(result.passed)
            self.assertEqual(
                model.last_request.response_contract,
                "patch_json",
            )
            self.assertIn(
                "return a + b",
                target.read_text(),
            )


if __name__ == "__main__":
    unittest.main()
