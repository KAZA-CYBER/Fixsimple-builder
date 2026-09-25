#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import subprocess
import shutil
import tempfile


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


class FixSimpleBuilder:
    """
    Minimal A0 Builder heartbeat.

    This is intentionally small.
    It proves repository access, file editing,
    command execution, observation and reporting.
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()

    def read_file(self, relative_path: str) -> str:
        path = self.repo_path / relative_path
        return path.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        path = self.repo_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        if path.suffix == ".py":
            try:
                cache_path = Path(
                    importlib.util.cache_from_source(str(path))
                )
            except (NotImplementedError, ValueError):
                cache_path = None

            if cache_path is not None:
                cache_path.unlink(missing_ok=True)

    def write_files_transactionally(
        self,
        pending_writes: dict[str, str],
    ) -> None:
        originals = {
            path: self.read_file(path)
            for path in pending_writes
        }
        written = []

        try:
            for path, content in pending_writes.items():
                self.write_file(path, content)
                written.append(path)
        except Exception:
            for path in reversed(written):
                self.write_file(path, originals[path])
            raise

    def verify_pending_writes(
        self,
        pending_writes: dict[str, str],
        command: str,
    ) -> CommandResult:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "repo"
            shutil.copytree(
                self.repo_path,
                sandbox,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    "runs",
                ),
            )

            sandbox_builder = FixSimpleBuilder(sandbox)

            for path, content in pending_writes.items():
                sandbox_builder.write_file(path, content)

            return sandbox_builder.run(command)

    def run(self, command: str) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=self.repo_path,
            shell=True,
            text=True,
            capture_output=True,
        )

        return CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def main() -> None:
    repo = Path.cwd()
    builder = FixSimpleBuilder(repo)

    print("FixSimple Builder A0")
    print(f"Repository: {repo}")
    print()

    result = builder.run("git status --short")

    print("Tool: shell")
    print(f"Command: {result.command}")
    print(f"Exit code: {result.returncode}")

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    print()
    print("HEARTBEAT:", "PASS" if result.passed else "FAIL")


if __name__ == "__main__":
    main()
