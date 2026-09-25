import json
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import ModelRequest
from remote_openai_model import RemoteOpenAIModel


class RemoteResponseValidationTests(unittest.TestCase):

    def test_missing_choices_is_reported_as_runtime_error(self):
        fake = subprocess.CompletedProcess(
            args=["curl"],
            returncode=0,
            stdout=json.dumps({"object": "chat.completion"}),
            stderr="",
        )

        model = RemoteOpenAIModel(
            base_url="https://example.invalid",
            model="test-model",
        )

        with patch(
            "remote_openai_model.subprocess.run",
            return_value=fake,
        ):
            with self.assertRaises(RuntimeError) as raised:
                model.complete(
                    ModelRequest(
                        task="Return corrected source.",
                        context="FILE: demo.py\nx = 1",
                    )
                )

            self.assertIn(
                "choices",
                str(raised.exception).lower(),
            )


if __name__ == "__main__":
    unittest.main()
