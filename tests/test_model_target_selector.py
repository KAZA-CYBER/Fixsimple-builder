import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import FixSimpleModel, ModelResponse
from model_target_selector import select_targets_with_model


class FakeModel(FixSimpleModel):
    def __init__(self, content):
        self.content = content
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return ModelResponse(
            content=self.content,
            model="fake-model",
        )


class ModelTargetSelectorTests(unittest.TestCase):

    def test_accepts_candidates_selected_by_model(self):
        model = FakeModel(
            '{"targets":["src/service.py","tests/test_service.py"]}'
        )

        result = select_targets_with_model(
            "Repair parse_total.",
            [
                "src/service.py",
                "tests/test_service.py",
                "README.md",
            ],
            {
                "src/service.py": {
                    "definitions": ["parse_total"],
                },
            },
            model,
            max_targets=2,
        )

        self.assertEqual(
            result,
            [
                "src/service.py",
                "tests/test_service.py",
            ],
        )
        self.assertEqual(
            model.requests[0].response_contract,
            "target_selection_json",
        )

    def test_rejects_invented_target(self):
        model = FakeModel(
            '{"targets":["src/invented.py"]}'
        )

        with self.assertRaisesRegex(
            ValueError,
            "non-candidate",
        ):
            select_targets_with_model(
                "Repair parser.",
                ["src/service.py"],
                {},
                model,
            )

    def test_rejects_duplicate_targets(self):
        model = FakeModel(
            '{"targets":["src/service.py","src/service.py"]}'
        )

        with self.assertRaisesRegex(
            ValueError,
            "unique",
        ):
            select_targets_with_model(
                "Repair parser.",
                ["src/service.py"],
                {},
                model,
            )

    def test_rejects_too_many_targets(self):
        model = FakeModel(
            '{"targets":["a.py","b.py"]}'
        )

        with self.assertRaisesRegex(
            ValueError,
            "too many",
        ):
            select_targets_with_model(
                "Repair parser.",
                ["a.py", "b.py"],
                {},
                model,
                max_targets=1,
            )

    def test_rejects_invalid_shape(self):
        model = FakeModel(
            '{"targets":[],"reason":"extra"}'
        )

        with self.assertRaisesRegex(
            ValueError,
            "only targets",
        ):
            select_targets_with_model(
                "Repair parser.",
                ["a.py"],
                {},
                model,
            )


if __name__ == "__main__":
    unittest.main()
