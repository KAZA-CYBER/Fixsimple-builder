import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from repository_understanding import (
    build_repository_map,
    understand_python_file,
)


class RepositoryUnderstandingTests(unittest.TestCase):

    def test_extracts_python_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            target = root / "src" / "service.py"
            target.write_text(
                "import json\n"
                "from pathlib import Path\n\n"
                "class Parser:\n"
                "    def parse_total(self, value):\n"
                "        return json.loads(value)\n"
            )

            result = understand_python_file(
                root,
                "src/service.py",
            )

            self.assertEqual(
                result.definitions,
                ["Parser", "parse_total"],
            )
            self.assertIn("json", result.imports)
            self.assertIn("pathlib", result.imports)
            self.assertIn("loads", result.references)

    def test_builds_map_for_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text(
                "def run_app():\n"
                "    return 1\n"
            )
            (root / "README.md").write_text("# Repo\n")

            result = build_repository_map(
                root,
                [
                    "README.md",
                    "src/app.py",
                ],
            )

            self.assertEqual(
                sorted(result),
                [
                    "README.md",
                    "src/app.py",
                ],
            )
            self.assertEqual(
                result["src/app.py"]["definitions"],
                ["run_app"],
            )
            self.assertEqual(
                result["README.md"]["language"],
                "text",
            )


if __name__ == "__main__":
    unittest.main()
