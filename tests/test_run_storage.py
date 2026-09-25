import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from run_storage import write_json_atomic


class RunStorageTests(unittest.TestCase):

    def test_write_json_atomic_replaces_target_without_temp_leftover(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "run.json"

            write_json_atomic(
                target,
                {
                    "status": "running",
                    "value": 1,
                },
            )

            data = json.loads(target.read_text())

            self.assertEqual(
                data["status"],
                "running",
            )
            self.assertEqual(
                data["value"],
                1,
            )
            self.assertFalse(
                (root / "run.json.tmp").exists()
            )


if __name__ == "__main__":
    unittest.main()
