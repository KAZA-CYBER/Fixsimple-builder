import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_interface import ModelRequest
from remote_openai_model import RemoteOpenAIModel


class FakeLifecycle:
    def __init__(self):
        self.events = []

    def begin_request(self, *, request_timeout):
        self.events.append(
            ("begin", request_timeout)
        )
        return "lease-1"

    def end_request(self, lease_id):
        self.events.append(
            ("end", lease_id)
        )


class RemoteLifecycleTests(unittest.TestCase):

    def test_remote_request_is_wrapped_in_lifecycle_lease(self):
        lifecycle = FakeLifecycle()
        model = RemoteOpenAIModel(
            base_url="https://pod.example",
            model="test-model",
            timeout=17,
            lifecycle=lifecycle,
        )

        completed = Mock()
        completed.returncode = 0
        completed.stdout = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "x = 1"
                        }
                    }
                ]
            }
        )
        completed.stderr = ""

        with patch(
            "remote_openai_model.subprocess.run",
            return_value=completed,
        ):
            response = model.complete(
                ModelRequest(
                    task="repair",
                    context="FILE: x.py\nx = 0",
                )
            )

        self.assertEqual(
            response.content,
            "x = 1",
        )
        self.assertEqual(
            lifecycle.events,
            [
                ("begin", 17),
                ("end", "lease-1"),
            ],
        )

    def test_lease_released_when_remote_request_fails(self):
        lifecycle = FakeLifecycle()
        model = RemoteOpenAIModel(
            base_url="https://pod.example",
            model="test-model",
            lifecycle=lifecycle,
        )

        completed = Mock()
        completed.returncode = 22
        completed.stdout = "failure"
        completed.stderr = "failure"

        with patch(
            "remote_openai_model.subprocess.run",
            return_value=completed,
        ):
            with self.assertRaises(RuntimeError):
                model.complete(
                    ModelRequest(
                        task="repair",
                        context="FILE: x.py\nx = 0",
                    )
                )

        self.assertEqual(
            lifecycle.events[-1],
            ("end", "lease-1"),
        )


if __name__ == "__main__":
    unittest.main()
