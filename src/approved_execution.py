import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from model_interface import FixSimpleModel
from run_storage import write_json_atomic
from target_approval import build_approved_task
from task_executor import TaskExecutor


@dataclass
class ApprovedExecutionReport:
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


def _read_audit(path: Path) -> list[dict]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def execute_approved_run(
    repo_root: Path,
    run_dir: Path,
    model: FixSimpleModel,
    *,
    model_name: str,
) -> ApprovedExecutionReport:
    repo_root = repo_root.resolve()
    run_dir = run_dir.resolve()

    task = build_approved_task(
        repo_root,
        run_dir,
    )

    manifest_path = run_dir / "run.json"
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError("run manifest must be a JSON object")

    prior_audit = _read_audit(
        run_dir / "audit.json"
    )

    execution_started_at = datetime.now(
        timezone.utc
    ).isoformat()

    manifest["status"] = "running"
    manifest["finished_at"] = None
    manifest["execution_started_at"] = execution_started_at
    manifest["pid"] = os.getpid()
    manifest["model"] = model_name

    write_json_atomic(
        manifest_path,
        manifest,
    )

    try:
        executor = TaskExecutor(repo_root, model)
        result = executor.execute(task)

        combined_audit = (
            prior_audit
            + list(getattr(result, "audit", []))
        )

        report = ApprovedExecutionReport(
            task_id=result.task_id,
            passed=result.passed,
            attempts=result.attempts,
            verification_output=(
                result.final_verification_output.strip()
            ),
            model=model_name,
            targets=list(task.target_files),
            rolled_back=getattr(
                result,
                "rolled_back",
                False,
            ),
            audit=combined_audit,
        )

        write_json_atomic(
            run_dir / "report.json",
            report.to_dict(),
        )
        write_json_atomic(
            run_dir / "audit.json",
            combined_audit,
        )

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        manifest["status"] = (
            "passed" if report.passed else "failed"
        )
        manifest["finished_at"] = finished_at
        manifest["execution_finished_at"] = finished_at

        write_json_atomic(
            manifest_path,
            manifest,
        )

        return report

    except Exception as exc:
        error_event = {
            "event": "runtime_exception",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
        combined_audit = prior_audit + [error_event]

        write_json_atomic(
            run_dir / "error.json",
            error_event,
        )
        write_json_atomic(
            run_dir / "audit.json",
            combined_audit,
        )

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        manifest["status"] = "error"
        manifest["finished_at"] = finished_at
        manifest["execution_finished_at"] = finished_at

        write_json_atomic(
            manifest_path,
            manifest,
        )

        raise
