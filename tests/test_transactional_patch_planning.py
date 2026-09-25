import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import FixSimpleModel, ModelResponse
from task_contract import BuilderTask
from task_executor import TaskExecutor


class InvalidSecondPatchModel(FixSimpleModel):
    supports_patch_edits = True

    def complete(self, request):
        return ModelResponse(
            content=json.dumps(
                {
                    "patches": [
                        {
                            "path": "a.py",
                            "old": "x = 0",
                            "new": "x = 1",
                        },
                        {
                            "path": "b.py",
                            "old": "missing text",
                            "new": "y = 2",
                        },
                    ]
                }
            ),
            model="invalid-second-patch",
        )


class TransactionalPatchPlanningTests(unittest.TestCase):

    def test_invalid_later_patch_causes_zero_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "a.py").write_text("x = 0\n")
            (root / "b.py").write_text("y = 0\n")
            (root / "verify.py").write_text(
                "raise SystemExit(1)\n"
            )

            task = BuilderTask(
                task_id="V0.50-TRANSACTIONAL-001",
                instruction="Repair both files.",
                target_files=["a.py", "b.py"],
                verification_command="python3 -B verify.py",
                max_repair_iterations=1,
            )

            executor = TaskExecutor(
                repo_root=root,
                model=InvalidSecondPatchModel(),
            )

            writes = []
            original_write = executor.builder.write_file

            def tracking_write(path, content):
                writes.append((path, content))
                return original_write(path, content)

            with patch.object(
                executor.builder,
                "write_file",
                side_effect=tracking_write,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "match exactly once",
                ):
                    executor.execute(task)

            self.assertEqual(writes, [])
            self.assertEqual(
                (root / "a.py").read_text(),
                "x = 0\n",
            )
            self.assertEqual(
                (root / "b.py").read_text(),
                "y = 0\n",
            )


if __name__ == "__main__":
    unittest.main()
