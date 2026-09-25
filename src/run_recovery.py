import json
import os
from datetime import datetime, timezone
from pathlib import Path

from run_storage import write_json_atomic


def mark_stale_runs(
    runs_root: Path,
    stale_after_seconds: int,
) -> list[str]:
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be >= 0")

    if not runs_root.exists():
        return []

    now = datetime.now(timezone.utc)
    interrupted = []

    for run_dir in runs_root.iterdir():
        if not run_dir.is_dir():
            continue

        manifest_path = run_dir / "run.json"
        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(
                manifest_path.read_text()
            )
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(manifest, dict):
            continue

        if manifest.get("status") != "running":
            continue

        started_at_raw = manifest.get("started_at")
        if not started_at_raw:
            continue

        try:
            started_at = datetime.fromisoformat(
                started_at_raw
            )
        except (TypeError, ValueError):
            continue

        if started_at.tzinfo is None:
            continue

        age_seconds = (now - started_at).total_seconds()

        if age_seconds < stale_after_seconds:
            continue

        pid = manifest.get("pid")

        if isinstance(pid, int) and pid > 0:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                interruption_reason = (
                    "stale_running_process_not_found"
                )
            except PermissionError:
                continue
            else:
                continue
        else:
            interruption_reason = (
                "stale_running_missing_pid"
            )

        manifest["status"] = "interrupted"
        manifest["finished_at"] = now.isoformat()
        manifest["interruption_reason"] = (
            interruption_reason
        )

        write_json_atomic(
            manifest_path,
            manifest,
        )

        interrupted.append(run_dir.name)

    return interrupted
