import unittest
from unittest.mock import patch
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


    def test_transactional_write_restores_earlier_file_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = FixSimpleBuilder(root)

            (root / "a.py").write_text("a = 0\n")
            (root / "b.py").write_text("b = 0\n")

            original_write = builder.write_file
            failed_once = False

            def flaky_write(path, content):
                nonlocal failed_once
                if path == "b.py" and not failed_once:
                    failed_once = True
                    raise OSError("simulated write failure")
                return original_write(path, content)

            with patch.object(
                builder,
                "write_file",
                side_effect=flaky_write,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated write failure",
                ):
                    builder.write_files_transactionally(
                        {
                            "a.py": "a = 1\n",
                            "b.py": "b = 1\n",
                        }
                    )

            self.assertEqual(
                (root / "a.py").read_text(),
                "a = 0\n",
            )
            self.assertEqual(
                (root / "b.py").read_text(),
                "b = 0\n",
            )


    def test_transactional_write_rejects_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = FixSimpleBuilder(root)

            (root / "target.py").write_text("value = 1\n")

            expected = {
                "target.py": "value = 1\n",
            }

            (root / "target.py").write_text("value = 99\n")

            with self.assertRaisesRegex(
                RuntimeError,
                "target changed before commit",
            ):
                builder.write_files_transactionally(
                    {
                        "target.py": "value = 2\n",
                    },
                    expected_originals=expected,
                )

            self.assertEqual(
                (root / "target.py").read_text(),
                "value = 99\n",
            )


if __name__ == "__main__":
    unittest.main()
