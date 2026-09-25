import json
from datetime import datetime, timezone
from pathlib import Path

from run_storage import write_json_atomic
from task_contract import BuilderTask


APPROVABLE_STATUSES = {
    "discovery_required",
    "targets_selected",
}


def _read_json_object(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing {label}: {path.name}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {path.name}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object")

    return data


def approve_discovery_run(
    repo_root: Path,
    run_dir: Path,
    approved_targets: list[str],
) -> dict:
    repo_root = repo_root.resolve()
    run_dir = run_dir.resolve()

    if not approved_targets:
        raise ValueError("at least one approved target is required")

    if any(
        not isinstance(target, str) or not target.strip()
        for target in approved_targets
    ):
        raise ValueError("approved targets must be non-empty strings")

    if len(set(approved_targets)) != len(approved_targets):
        raise ValueError("approved targets must be unique")

    task = _read_json_object(
        run_dir / "task.json",
        "task artifact",
    )
    discovery = _read_json_object(
        run_dir / "discovery.json",
        "discovery artifact",
    )
    manifest = _read_json_object(
        run_dir / "run.json",
        "run manifest",
    )

    status = manifest.get("status")
    if status not in APPROVABLE_STATUSES:
        raise ValueError(
            "run is not awaiting target approval: "
            f"status={status}"
        )

    candidate_files = discovery.get("candidate_files")
    if not isinstance(candidate_files, list):
        raise ValueError("discovery candidate_files must be a list")

    candidate_set = set(candidate_files)
    unknown = sorted(set(approved_targets) - candidate_set)
    if unknown:
        raise ValueError(
            "approved targets are not discovery candidates: "
            + ", ".join(unknown)
        )

    protected_paths = task.get("protected_paths", [])
    if not isinstance(protected_paths, list):
        raise ValueError("protected_paths must be a list")

    root = repo_root.resolve()

    for relative in approved_targets:
        candidate = (root / relative).resolve()

        if root not in candidate.parents and candidate != root:
            raise ValueError(
                f"approved target escapes repository: {relative}"
            )

        if not candidate.exists():
            raise FileNotFoundError(
                f"approved target does not exist: {relative}"
            )

        for protected in protected_paths:
            protected_path = (root / protected).resolve()

            if (
                candidate == protected_path
                or protected_path in candidate.parents
            ):
                raise PermissionError(
                    f"approved target is protected: {relative}"
                )

    approved_at = datetime.now(timezone.utc).isoformat()
    approval = {
        "task_id": task.get("task_id"),
        "approved_targets": list(approved_targets),
        "approved_at": approved_at,
        "source_status": status,
    }

    write_json_atomic(
        run_dir / "approval.json",
        approval,
    )

    audit_path = run_dir / "audit.json"
    audit = []

    if audit_path.exists():
        try:
            existing_audit = json.loads(
                audit_path.read_text()
            )
            if isinstance(existing_audit, list):
                audit = existing_audit
        except (OSError, json.JSONDecodeError):
            audit = []

    audit.append(
        {
            "event": "targets_approved",
            "approved_targets": list(approved_targets),
            "approved_at": approved_at,
        }
    )

    write_json_atomic(
        audit_path,
        audit,
    )

    manifest["status"] = "approved"
    manifest["approved_at"] = approved_at
    manifest["approved_targets"] = list(approved_targets)

    write_json_atomic(
        run_dir / "run.json",
        manifest,
    )

    return approval


def build_approved_task(
    repo_root: Path,
    run_dir: Path,
) -> BuilderTask:
    repo_root = repo_root.resolve()
    run_dir = run_dir.resolve()

    task_data = _read_json_object(
        run_dir / "task.json",
        "task artifact",
    )
    approval = _read_json_object(
        run_dir / "approval.json",
        "approval artifact",
    )
    manifest = _read_json_object(
        run_dir / "run.json",
        "run manifest",
    )

    if manifest.get("status") != "approved":
        raise ValueError(
            "run is not approved for execution: "
            f"status={manifest.get('status')}"
        )

    task_id = task_data.get("task_id")
    if approval.get("task_id") != task_id:
        raise ValueError(
            "approval task_id does not match task artifact"
        )

    approved_targets = approval.get("approved_targets")
    if not isinstance(approved_targets, list) or not approved_targets:
        raise ValueError(
            "approval must contain approved_targets"
        )

    task = BuilderTask(
        task_id=task_id,
        instruction=task_data.get("instruction", ""),
        target_files=list(approved_targets),
        verification_command=task_data.get(
            "verification_command",
            "",
        ),
        max_repair_iterations=task_data.get(
            "max_repair_iterations",
            2,
        ),
        protected_paths=task_data.get(
            "protected_paths",
            [],
        ),
    )

    task.validate(repo_root)
    return task
