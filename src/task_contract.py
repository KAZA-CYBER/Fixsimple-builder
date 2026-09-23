from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BuilderTask:
    task_id: str
    instruction: str
    target_files: list[str]
    verification_command: str
    max_repair_iterations: int = 2
    protected_paths: list[str] = field(default_factory=list)

    def validate(self, repo_root: Path) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id is required")

        if not self.instruction.strip():
            raise ValueError("instruction is required")

        if not self.target_files:
            raise ValueError("at least one target file is required")

        if not self.verification_command.strip():
            raise ValueError("verification_command is required")

        if self.max_repair_iterations < 1:
            raise ValueError("max_repair_iterations must be >= 1")

        root = repo_root.resolve()

        for relative in self.target_files:
            candidate = (root / relative).resolve()

            if root not in candidate.parents and candidate != root:
                raise ValueError(
                    f"target file escapes repository: {relative}"
                )

            if not candidate.exists():
                raise FileNotFoundError(
                    f"target file does not exist: {relative}"
                )

            for protected in self.protected_paths:
                protected_path = (root / protected).resolve()

                if (
                    candidate == protected_path
                    or protected_path in candidate.parents
                ):
                    raise PermissionError(
                        f"target file is protected: {relative}"
                    )
