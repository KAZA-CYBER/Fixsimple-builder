import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_interface import FixSimpleModel, ModelRequest, ModelResponse


class FakeModel(FixSimpleModel):
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content=f"PLAN: {request.task}",
            model="fake-a0-model",
        )


class ModelInterfaceTests(unittest.TestCase):

    def test_builder_owned_model_boundary(self):
        model = FakeModel()

        response = model.complete(
            ModelRequest(
                task="repair failing test",
                context="test failed",
            )
        )

        self.assertEqual(response.model, "fake-a0-model")
        self.assertEqual(
            response.content,
            "PLAN: repair failing test",
        )


if __name__ == "__main__":
    unittest.main()
