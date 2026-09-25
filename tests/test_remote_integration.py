import os
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import ModelRequest
from remote_openai_model import RemoteOpenAIModel


@unittest.skipUnless(
    os.environ.get("FIXSIMPLE_MODEL_BASE_URL"),
    "FIXSIMPLE_MODEL_BASE_URL not set",
)
class RemoteIntegrationTests(unittest.TestCase):

    def test_remote_model_round_trip(self):
        model = RemoteOpenAIModel(
            base_url=os.environ["FIXSIMPLE_MODEL_BASE_URL"],
            model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        )

        response = model.complete(
            ModelRequest(
                task=(
                    "Repair the Python function so it returns "
                    "the sum of a and b. Return only the complete "
                    "corrected Python source file."
                ),
                context=(
                    "FILE: demo.py\n"
                    "def add(a, b):\n"
                    "    return a - b\n\n"
                    "VERIFICATION FAILURE:\n"
                    "expected 5, got -1"
                ),
            )
        )

        self.assertEqual(
            response.model,
            "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        )
        self.assertIn(
            "return a + b",
            response.content,
        )


if __name__ == "__main__":
    unittest.main()
