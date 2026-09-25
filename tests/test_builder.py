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

    def test_python_write_invalidates_bytecode_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            builder = FixSimpleBuilder(repo)

            source = repo / "module.py"
            builder.write_file(
                "module.py",
                "value = 1\n",
            )

            cache = Path(
                __import__("importlib").util.cache_from_source(
                    str(source)
                )
            )
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(b"stale")

            self.assertTrue(cache.exists())

            builder.write_file(
                "module.py",
                "value = 2\n",
            )

            self.assertFalse(cache.exists())


if __name__ == "__main__":
    unittest.main()
