from pathlib import Path


DEFAULT_IGNORED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "runs",
    "models",
}


DEFAULT_SUFFIXES = {
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
}


def inspect_repository(
    repo_root: Path,
    *,
    suffixes: set[str] | None = None,
) -> list[str]:
    root = repo_root.resolve()
    allowed_suffixes = suffixes or DEFAULT_SUFFIXES

    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(
            part in DEFAULT_IGNORED_PARTS
            for part in relative.parts
        ):
            continue

        if path.suffix.lower() not in allowed_suffixes:
            continue

        files.append(relative.as_posix())

    return sorted(files)
