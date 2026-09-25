from dataclasses import dataclass
from pathlib import Path

from repository_inspector import inspect_repository
from task_contract import BuilderTask


@dataclass
class TaskIntakeResult:
    discovery_required: bool
    task: BuilderTask | None
    candidate_files: list[str]


def prepare_task_intake(
    repo_root: Path,
    data: dict,
) -> TaskIntakeResult:
    target_files = data.get("target_files")

    if target_files:
        task = BuilderTask(
            task_id=data["task_id"],
            instruction=data["instruction"],
            target_files=target_files,
            verification_command=data["verification_command"],
            max_repair_iterations=data.get(
                "max_repair_iterations",
                2,
            ),
            protected_paths=data.get(
                "protected_paths",
                [],
            ),
        )

        task.validate(repo_root)

        return TaskIntakeResult(
            discovery_required=False,
            task=task,
            candidate_files=[],
        )

    candidates = inspect_repository(repo_root)

    return TaskIntakeResult(
        discovery_required=True,
        task=None,
        candidate_files=candidates,
    )
