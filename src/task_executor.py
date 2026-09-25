import json
from dataclasses import dataclass
from pathlib import Path

from builder import FixSimpleBuilder
from model_interface import FixSimpleModel, ModelRequest
from patch_edit import apply_exact_patch, parse_patch_response
from task_contract import BuilderTask


@dataclass
class TaskExecutionResult:
    task_id: str
    passed: bool
    attempts: int
    final_verification_output: str
    audit: list[dict]
    rolled_back: bool = False


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

        original_contents = {
            relative_path: self.builder.read_file(relative_path)
            for relative_path in task.target_files
        }

        def restore_originals() -> None:
            for relative_path, content in original_contents.items():
                self.builder.write_file(
                    relative_path,
                    content,
                )

        audit = []

        verification = self.builder.run(
            task.verification_command
        )

        initial_output = (
            verification.stderr.strip()
            or verification.stdout.strip()
        )

        audit.append(
            {
                "event": "initial_verification",
                "passed": verification.passed,
                "output": initial_output,
            }
        )

        if verification.passed:
            return TaskExecutionResult(
                task_id=task.task_id,
                passed=True,
                attempts=0,
                final_verification_output=verification.stdout,
                audit=audit,
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

            if (
                len(task.target_files) == 1
                and getattr(
                    self.model,
                    "supports_patch_edits",
                    False,
                )
            ):
                response_contract = "patch_json"
            elif len(task.target_files) == 1:
                response_contract = "single_file"
            else:
                response_contract = "multi_file_json"

            request = ModelRequest(
                task=task.instruction,
                context=(
                    "\n\n".join(context_parts)
                    + "\n\nVERIFICATION FAILURE:\n"
                    + failure
                ),
                response_contract=response_contract,
            )

            try:
                response = self.model.complete(request)

                if response_contract == "patch_json":
                    target = task.target_files[0]
                    _, old, new = parse_patch_response(
                        response.content,
                        expected_target=target,
                    )
                    current = self.builder.read_file(target)
                    pending_writes = {
                        target: apply_exact_patch(
                            current,
                            old=old,
                            new=new,
                        )
                    }
                elif response_contract == "single_file":
                    pending_writes = {
                        task.target_files[0]: response.content,
                    }
                else:
                    try:
                        payload = json.loads(response.content)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            "multi-file model response is not valid JSON"
                        ) from exc

                    if not isinstance(payload, dict):
                        raise ValueError(
                            "multi-file model response must be "
                            "a JSON object"
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

                    pending_writes = {}

                    for relative_path in task.target_files:
                        content = files[relative_path]

                        if not isinstance(content, str):
                            raise ValueError(
                                "multi-file response content "
                                "must be text: "
                                + relative_path
                            )

                        pending_writes[relative_path] = content

                for relative_path, content in pending_writes.items():
                    self.builder.write_file(
                        relative_path,
                        content,
                    )

                verification = self.builder.run(
                    task.verification_command
                )

                attempt_output = (
                    verification.stderr.strip()
                    or verification.stdout.strip()
                )

                audit.append(
                    {
                        "event": "repair_attempt",
                        "attempt": attempt,
                        "response_contract": response_contract,
                        "targets": list(task.target_files),
                        "verification_passed": verification.passed,
                        "verification_output": attempt_output,
                    }
                )

            except Exception:
                restore_originals()
                raise

            if verification.passed:
                return TaskExecutionResult(
                    task_id=task.task_id,
                    passed=True,
                    attempts=attempt,
                    final_verification_output=verification.stdout,
                    audit=audit,
                )

        final_output = (
            verification.stderr
            or verification.stdout
        )

        restore_originals()

        audit.append(
            {
                "event": "rollback",
                "reason": "repair_iterations_exhausted",
                "targets": list(task.target_files),
            }
        )

        return TaskExecutionResult(
            task_id=task.task_id,
            passed=False,
            attempts=task.max_repair_iterations,
            final_verification_output=final_output,
            audit=audit,
            rolled_back=True,
        )
