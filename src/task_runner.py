import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from local_llama_model import LocalLlamaModel
from remote_openai_model import RemoteOpenAIModel
from task_contract import BuilderTask
from task_executor import TaskExecutor


@dataclass
class TaskRunReport:
    task_id: str
    passed: bool
    attempts: int
    verification_output: str
    model: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_model_config(config_file: Path) -> dict:
    if not config_file.exists():
        return {}

    data = json.loads(config_file.read_text())

    allowed = {
        "backend",
        "base_url",
        "remote_model",
        "local_model_path",
    }

    unknown = set(data) - allowed
    if unknown:
        raise ValueError(
            "unknown model config fields: "
            + ", ".join(sorted(unknown))
        )

    return data


def load_task(task_file: Path) -> BuilderTask:
    data = json.loads(task_file.read_text())

    allowed = {
        "task_id",
        "instruction",
        "target_files",
        "verification_command",
        "max_repair_iterations",
        "protected_paths",
    }

    unknown = set(data) - allowed
    if unknown:
        raise ValueError(
            "unknown task fields: " + ", ".join(sorted(unknown))
        )

    return BuilderTask(
        task_id=data["task_id"],
        instruction=data["instruction"],
        target_files=data["target_files"],
        verification_command=data["verification_command"],
        max_repair_iterations=data.get("max_repair_iterations", 2),
        protected_paths=data.get("protected_paths", []),
    )


def run_task(
    repo_root: Path,
    task_file: Path,
    model_path: Path,
    report_file: Optional[Path] = None,
    backend: str = "local",
    base_url: Optional[str] = None,
    remote_model: str = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
) -> TaskRunReport:
    repo_root = repo_root.resolve()
    task_file = task_file.resolve()
    model_path = model_path.resolve()

    task = load_task(task_file)
    task.validate(repo_root)

    if backend == "local":
        if not model_path.exists():
            raise FileNotFoundError(
                f"model does not exist: {model_path}"
            )
        model = LocalLlamaModel(str(model_path))
        model_name = "granite-4.0-1b-Q4_K_M-local"
    elif backend == "remote":
        if not base_url:
            raise ValueError(
                "base_url is required for remote backend"
            )
        model = RemoteOpenAIModel(
            base_url=base_url,
            model=remote_model,
        )
        model_name = remote_model
    else:
        raise ValueError(
            f"unsupported backend: {backend}"
        )

    executor = TaskExecutor(repo_root, model)
    result = executor.execute(task)

    report = TaskRunReport(
        task_id=result.task_id,
        passed=result.passed,
        attempts=result.attempts,
        verification_output=result.final_verification_output.strip(),
        model=model_name,
    )

    if report_file is not None:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(report.to_dict(), indent=2) + "\n"
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FixSimple Builder Task Runner"
    )

    parser.add_argument(
        "--task",
        required=True,
        type=Path,
        help="JSON task contract",
    )

    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="repository root",
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="local GGUF model override",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="optional JSON execution report",
    )

    parser.add_argument(
        "--backend",
        choices=("local", "remote"),
        default=None,
        help="model backend override",
    )

    parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible remote model base URL",
    )

    parser.add_argument(
        "--remote-model",
        default=None,
        help="remote model identifier override",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/model.json"),
        help="model configuration JSON",
    )

    args = parser.parse_args()

    config = load_model_config(args.config)

    backend = (
        args.backend
        or config.get("backend")
        or "local"
    )

    model_path = (
        args.model
        or Path(
            config.get(
                "local_model_path",
                "models/granite-4.0-1b-Q4_K_M.gguf",
            )
        )
    )

    base_url = (
        args.base_url
        or config.get("base_url")
    )

    remote_model = (
        args.remote_model
        or config.get("remote_model")
        or "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
    )

    report = run_task(
        repo_root=args.repo,
        task_file=args.task,
        model_path=model_path,
        report_file=args.report,
        backend=backend,
        base_url=base_url,
        remote_model=remote_model,
    )

    print("=== FIXSIMPLE BUILDER TASK REPORT ===")
    print(json.dumps(report.to_dict(), indent=2))

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
