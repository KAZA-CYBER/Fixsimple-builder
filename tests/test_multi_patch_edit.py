import json
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from patch_edit import (
    apply_exact_patch,
    parse_multi_patch_response,
)


class MultiPatchEditingTests(unittest.TestCase):

    def test_parses_exact_target_set(self):
        parsed = parse_multi_patch_response(
            json.dumps(
                {
                    "patches": [
                        {
                            "path": "a.py",
                            "old": "x = 1",
                            "new": "x = 2",
                        },
                        {
                            "path": "b.py",
                            "old": "y = 1",
                            "new": "y = 3",
                        },
                    ]
                }
            ),
            expected_targets=["a.py", "b.py"],
        )

        self.assertEqual(
            [item[0] for item in parsed],
            ["a.py", "b.py"],
        )

    def test_rejects_missing_target(self):
        with self.assertRaisesRegex(
            ValueError,
            "multi-patch target mismatch",
        ):
            parse_multi_patch_response(
                json.dumps(
                    {
                        "patches": [
                            {
                                "path": "a.py",
                                "old": "x",
                                "new": "y",
                            }
                        ]
                    }
                ),
                expected_targets=["a.py", "b.py"],
            )

    def test_rejects_unexpected_target(self):
        with self.assertRaisesRegex(
            ValueError,
            "unexpected target",
        ):
            parse_multi_patch_response(
                json.dumps(
                    {
                        "patches": [
                            {
                                "path": "a.py",
                                "old": "x",
                                "new": "y",
                            },
                            {
                                "path": "secret.py",
                                "old": "s",
                                "new": "t",
                            },
                        ]
                    }
                ),
                expected_targets=["a.py", "b.py"],
            )

    def test_rejects_duplicate_target(self):
        with self.assertRaisesRegex(
            ValueError,
            "duplicated",
        ):
            parse_multi_patch_response(
                json.dumps(
                    {
                        "patches": [
                            {
                                "path": "a.py",
                                "old": "x",
                                "new": "y",
                            },
                            {
                                "path": "a.py",
                                "old": "z",
                                "new": "w",
                            },
                        ]
                    }
                ),
                expected_targets=["a.py", "b.py"],
            )

    def test_each_patch_is_exact(self):
        self.assertEqual(
            apply_exact_patch(
                "alpha\nbeta\n",
                old="beta",
                new="gamma",
            ),
            "alpha\ngamma\n",
        )


if __name__ == "__main__":
    unittest.main()
