import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from task_runner import load_task, resolve_model_settings, run_task


class TaskRunnerTests(unittest.TestCase):

    def test_load_valid_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"

            path.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-001",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "python3 test.py",
                        "max_repair_iterations": 2,
                    }
                )
            )

            task = load_task(path)

            self.assertEqual(task.task_id, "RUNNER-001")
            self.assertEqual(task.target_files, ["target.py"])
            self.assertEqual(task.max_repair_iterations, 2)

    def test_reject_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"

            path.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-002",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                        "invented_permission": True,
                    }
                )
            )

            with self.assertRaises(ValueError):
                load_task(path)


    def test_remote_requires_base_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.py"
            target.write_text("x = 1\n")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-REMOTE-001",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            with self.assertRaisesRegex(
                ValueError,
                "base_url is required for remote backend",
            ):
                run_task(
                    repo_root=root,
                    task_file=task_file,
                    model_path=root / "unused.gguf",
                    backend="remote",
                )

    def test_reject_invalid_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.py"
            target.write_text("x = 1\n")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-BACKEND-001",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            with self.assertRaisesRegex(
                ValueError,
                "unsupported backend: invented",
            ):
                run_task(
                    repo_root=root,
                    task_file=task_file,
                    model_path=root / "unused.gguf",
                    backend="invented",
                )

    def test_remote_backend_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.py"
            target.write_text("x = 1\n")

            task_file = root / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "RUNNER-REMOTE-002",
                        "instruction": "Repair target.",
                        "target_files": ["target.py"],
                        "verification_command": "true",
                    }
                )
            )

            class FakeResult:
                task_id = "RUNNER-REMOTE-002"
                passed = True
                attempts = 1
                final_verification_output = "PASS"

            with patch("task_runner.RemoteOpenAIModel") as model_cls:
                with patch("task_runner.TaskExecutor") as executor_cls:
                    executor_cls.return_value.execute.return_value = FakeResult()

                    report = run_task(
                        repo_root=root,
                        task_file=task_file,
                        model_path=root / "unused.gguf",
                        backend="remote",
                        base_url="https://example.invalid",
                        remote_model="test-remote-model",
                    )

                    model_cls.assert_called_once_with(
                        base_url="https://example.invalid",
                        model="test-remote-model",
                    )
                    self.assertTrue(report.passed)
                    self.assertEqual(report.model, "test-remote-model")


    def test_model_settings_defaults(self):
        settings = resolve_model_settings()

        self.assertEqual(settings["backend"], "local")
        self.assertEqual(
            settings["model_path"],
            Path("models/granite-4.0-1b-Q4_K_M.gguf"),
        )
        self.assertIsNone(settings["base_url"])
        self.assertEqual(
            settings["remote_model"],
            "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        )

    def test_model_settings_config_overrides_defaults(self):
        settings = resolve_model_settings(
            config={
                "backend": "remote",
                "base_url": "https://config.example",
                "remote_model": "config-model",
                "local_model_path": "models/config.gguf",
            },
        )

        self.assertEqual(settings["backend"], "remote")
        self.assertEqual(
            settings["model_path"],
            Path("models/config.gguf"),
        )
        self.assertEqual(
            settings["base_url"],
            "https://config.example",
        )
        self.assertEqual(
            settings["remote_model"],
            "config-model",
        )

    def test_model_settings_env_overrides_config_base_url(self):
        settings = resolve_model_settings(
            config={
                "base_url": "https://config.example",
            },
            environ={
                "FIXSIMPLE_MODEL_BASE_URL":
                    "https://env.example",
            },
        )

        self.assertEqual(
            settings["base_url"],
            "https://env.example",
        )

    def test_model_settings_cli_overrides_env_and_config(self):
        settings = resolve_model_settings(
            cli_backend="local",
            cli_model_path=Path("models/cli.gguf"),
            cli_base_url="https://cli.example",
            cli_remote_model="cli-model",
            config={
                "backend": "remote",
                "base_url": "https://config.example",
                "remote_model": "config-model",
                "local_model_path": "models/config.gguf",
            },
            environ={
                "FIXSIMPLE_MODEL_BASE_URL":
                    "https://env.example",
            },
        )

        self.assertEqual(settings["backend"], "local")
        self.assertEqual(
            settings["model_path"],
            Path("models/cli.gguf"),
        )
        self.assertEqual(
            settings["base_url"],
            "https://cli.example",
        )
        self.assertEqual(
            settings["remote_model"],
            "cli-model",
        )


if __name__ == "__main__":
    unittest.main()
