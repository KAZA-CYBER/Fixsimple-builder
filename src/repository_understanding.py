import ast
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileUnderstanding:
    path: str
    language: str
    imports: list[str]
    definitions: list[str]
    references: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _unique_sorted(values) -> list[str]:
    return sorted({value for value in values if value})


def understand_python_file(
    repo_root: Path,
    relative_path: str,
) -> FileUnderstanding:
    root = repo_root.resolve()
    path = (root / relative_path).resolve()

    if root not in path.parents and path != root:
        raise ValueError(
            f"file escapes repository: {relative_path}"
        )

    source = path.read_text()
    tree = ast.parse(source, filename=relative_path)

    imports = []
    definitions = []
    references = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                alias.name
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
            imports.extend(
                alias.name
                for alias in node.names
            )
        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            definitions.append(node.name)
        elif isinstance(node, ast.Name):
            references.append(node.id)
        elif isinstance(node, ast.Attribute):
            references.append(node.attr)

    return FileUnderstanding(
        path=relative_path,
        language="python",
        imports=_unique_sorted(imports),
        definitions=_unique_sorted(definitions),
        references=_unique_sorted(references),
    )


def understand_file(
    repo_root: Path,
    relative_path: str,
) -> FileUnderstanding:
    path = Path(relative_path)

    if path.suffix.lower() == ".py":
        try:
            return understand_python_file(
                repo_root,
                relative_path,
            )
        except SyntaxError:
            pass

    return FileUnderstanding(
        path=relative_path,
        language="text",
        imports=[],
        definitions=[],
        references=[],
    )


def build_repository_map(
    repo_root: Path,
    candidate_files: list[str],
) -> dict[str, dict]:
    result = {}

    for relative_path in candidate_files:
        result[relative_path] = understand_file(
            repo_root,
            relative_path,
        ).to_dict()

    return result
