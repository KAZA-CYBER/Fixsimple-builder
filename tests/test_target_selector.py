import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from target_selector import select_targets


class TargetSelectorTests(unittest.TestCase):

    def test_selects_matching_targets(self):
        result = select_targets(
            "Repair the inventory parser.",
            [
                "src/inventory_parser.py",
                "src/payment_service.py",
                "tests/test_inventory_parser.py",
            ],
        )

        self.assertEqual(
            result,
            [
                "src/inventory_parser.py",
                "tests/test_inventory_parser.py",
            ],
        )

    def test_respects_max_targets(self):
        result = select_targets(
            "Repair inventory parser.",
            [
                "src/inventory_parser.py",
                "tests/test_inventory_parser.py",
            ],
            max_targets=1,
        )

        self.assertEqual(
            result,
            ["src/inventory_parser.py"],
        )

    def test_returns_empty_when_nothing_matches(self):
        result = select_targets(
            "Repair inventory parser.",
            [
                "src/payment_service.py",
                "README.md",
            ],
        )

        self.assertEqual(result, [])

    def test_uses_repository_content_when_path_does_not_match(self):
        result = select_targets(
            "Repair parse_total.",
            [
                "src/service.py",
                "src/payment.py",
            ],
            repository_map={
                "src/service.py": {
                    "imports": [],
                    "definitions": [
                        "Parser",
                        "parse_total",
                    ],
                    "references": [],
                },
                "src/payment.py": {
                    "imports": [],
                    "definitions": [
                        "charge_card",
                    ],
                    "references": [],
                },
            },
        )

        self.assertEqual(
            result,
            ["src/service.py"],
        )

    def test_path_match_outweighs_content_only_match(self):
        result = select_targets(
            "Repair inventory parser.",
            [
                "src/inventory_parser.py",
                "src/service.py",
            ],
            repository_map={
                "src/inventory_parser.py": {
                    "imports": [],
                    "definitions": [],
                    "references": [],
                },
                "src/service.py": {
                    "imports": [],
                    "definitions": [
                        "inventory_parser",
                    ],
                    "references": [],
                },
            },
        )

        self.assertEqual(
            result[0],
            "src/inventory_parser.py",
        )

    def test_rejects_invalid_max_targets(self):
        with self.assertRaises(ValueError):
            select_targets(
                "Repair app.",
                ["src/app.py"],
                max_targets=0,
            )


if __name__ == "__main__":
    unittest.main()
