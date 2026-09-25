import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
    targets: list[str]
    rolled_back: bool
    audit: list[dict]

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


def resolve_model_settings(
    *,
    cli_backend=None,
    cli_model_path=None,
    cli_base_url=None,
    cli_remote_model=None,
    config=None,
    environ=None,
):
    config = config or {}
    environ = environ or {}

    backend = (
        cli_backend
        or config.get("backend")
        or "local"
    )

    model_path = (
        cli_model_path
        or Path(
            config.get(
                "local_model_path",
                "models/granite-4.0-1b-Q4_K_M.gguf",
            )
        )
    )

    base_url = (
        cli_base_url
        or environ.get("FIXSIMPLE_MODEL_BASE_URL")
        or config.get("base_url")
    )

    remote_model = (
        cli_remote_model
        or config.get("remote_model")
        or "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
    )

    return {
        "backend": backend,
        "model_path": Path(model_path),
        "base_url": base_url,
        "remote_model": remote_model,
    }


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
    runs_root: Optional[Path] = None,
) -> TaskRunReport:
    repo_root = repo_root.resolve()
    task_file = task_file.resolve()
    model_path = model_path.resolve()

    task = load_task(task_file)
    task.validate(repo_root)

    if runs_root is None:
        runs_root = repo_root / "runs"

    run_id = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ"
    )
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "task.json").write_text(
        json.dumps(
            json.loads(task_file.read_text()),
            indent=2,
        )
        + "\n"
    )

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
        targets=list(task.target_files),
        rolled_back=getattr(result, "rolled_back", False),
        audit=getattr(result, "audit", []),
    )

    run_report = report.to_dict()

    (run_dir / "report.json").write_text(
        json.dumps(run_report, indent=2) + "\n"
    )

    (run_dir / "audit.json").write_text(
        json.dumps(report.audit, indent=2) + "\n"
    )

    if report_file is not None:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(run_report, indent=2) + "\n"
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

    settings = resolve_model_settings(
        cli_backend=args.backend,
        cli_model_path=args.model,
        cli_base_url=args.base_url,
        cli_remote_model=args.remote_model,
        config=config,
        environ=os.environ,
    )

    report = run_task(
        repo_root=args.repo,
        task_file=args.task,
        model_path=settings["model_path"],
        report_file=args.report,
        backend=settings["backend"],
        base_url=settings["base_url"],
        remote_model=settings["remote_model"],
    )

    print("=== FIXSIMPLE BUILDER TASK REPORT ===")
    print(json.dumps(report.to_dict(), indent=2))

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
