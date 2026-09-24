import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from local_llama_model import LocalLlamaModel
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
) -> TaskRunReport:
    repo_root = repo_root.resolve()
    task_file = task_file.resolve()
    model_path = model_path.resolve()

    task = load_task(task_file)
    task.validate(repo_root)

    if not model_path.exists():
        raise FileNotFoundError(
            f"model does not exist: {model_path}"
        )

    model = LocalLlamaModel(str(model_path))
    executor = TaskExecutor(repo_root, model)
    result = executor.execute(task)

    report = TaskRunReport(
        task_id=result.task_id,
        passed=result.passed,
        attempts=result.attempts,
        verification_output=result.final_verification_output.strip(),
        model="granite-4.0-1b-Q4_K_M-local",
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
        default=Path("models/granite-4.0-1b-Q4_K_M.gguf"),
        help="local GGUF model",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="optional JSON execution report",
    )

    args = parser.parse_args()

    report = run_task(
        repo_root=args.repo,
        task_file=args.task,
        model_path=args.model,
        report_file=args.report,
    )

    print("=== FIXSIMPLE BUILDER TASK REPORT ===")
    print(json.dumps(report.to_dict(), indent=2))

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
