import json
from dataclasses import dataclass
from pathlib import Path

from builder import FixSimpleBuilder
from model_interface import FixSimpleModel, ModelRequest
from task_contract import BuilderTask


@dataclass
class TaskExecutionResult:
    task_id: str
    passed: bool
    attempts: int
    final_verification_output: str


class TaskExecutor:
    def __init__(
        self,
        repo_root: Path,
        model: FixSimpleModel,
    ):
        self.repo_root = repo_root.resolve()
        self.builder = FixSimpleBuilder(self.repo_root)
        self.model = model

    def execute(self, task: BuilderTask) -> TaskExecutionResult:
        task.validate(self.repo_root)

        verification = self.builder.run(
            task.verification_command
        )

        if verification.passed:
            return TaskExecutionResult(
                task_id=task.task_id,
                passed=True,
                attempts=0,
                final_verification_output=verification.stdout,
            )

        for attempt in range(1, task.max_repair_iterations + 1):
            context_parts = []

            for relative_path in task.target_files:
                content = self.builder.read_file(relative_path)
                context_parts.append(
                    f"FILE: {relative_path}\n"
                    f"{content}"
                )

            failure = (
                verification.stderr.strip()
                or verification.stdout.strip()
            )

            response_contract = (
                "single_file"
                if len(task.target_files) == 1
                else "multi_file_json"
            )

            request = ModelRequest(
                task=task.instruction,
                context=(
                    "\n\n".join(context_parts)
                    + "\n\nVERIFICATION FAILURE:\n"
                    + failure
                ),
                response_contract=response_contract,
            )

            response = self.model.complete(request)

            if response_contract == "single_file":
                self.builder.write_file(
                    task.target_files[0],
                    response.content,
                )
            else:
                try:
                    payload = json.loads(response.content)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "multi-file model response is not valid JSON"
                    ) from exc

                if not isinstance(payload, dict):
                    raise ValueError(
                        "multi-file model response must be a JSON object"
                    )

                files = payload.get("files")
                if not isinstance(files, dict):
                    raise ValueError(
                        "multi-file model response must contain "
                        "a files object"
                    )

                expected = set(task.target_files)
                returned = set(files)

                if returned != expected:
                    missing = sorted(expected - returned)
                    extra = sorted(returned - expected)

                    raise ValueError(
                        "multi-file response target mismatch; "
                        f"missing={missing}, extra={extra}"
                    )

                for relative_path in task.target_files:
                    content = files[relative_path]

                    if not isinstance(content, str):
                        raise ValueError(
                            "multi-file response content must be text: "
                            + relative_path
                        )

                    self.builder.write_file(
                        relative_path,
                        content,
                    )

            verification = self.builder.run(
                task.verification_command
            )

            if verification.passed:
                return TaskExecutionResult(
                    task_id=task.task_id,
                    passed=True,
                    attempts=attempt,
                    final_verification_output=verification.stdout,
                )

        return TaskExecutionResult(
            task_id=task.task_id,
            passed=False,
            attempts=task.max_repair_iterations,
            final_verification_output=(
                verification.stderr
                or verification.stdout
            ),
        )
