import unittest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from builder import FixSimpleBuilder


class BuilderTests(unittest.TestCase):

    def test_read_write_and_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            builder = FixSimpleBuilder(repo)

            builder.write_file("sample.txt", "FixSimple")
            self.assertEqual(
                builder.read_file("sample.txt"),
                "FixSimple",
            )

            result = builder.run("python3 -c \"print('heartbeat')\"")

            self.assertTrue(result.passed)
            self.assertEqual(result.stdout.strip(), "heartbeat")


if __name__ == "__main__":
    unittest.main()
