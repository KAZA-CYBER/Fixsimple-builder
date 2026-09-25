import re
from pathlib import Path


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )
        if len(token) >= 2
    }


def _content_tokens(
    candidate: str,
    repository_map: dict[str, dict] | None,
) -> set[str]:
    if not repository_map:
        return set()

    metadata = repository_map.get(candidate)
    if not isinstance(metadata, dict):
        return set()

    values = []

    for field in (
        "imports",
        "definitions",
        "references",
    ):
        field_values = metadata.get(field, [])
        if isinstance(field_values, list):
            values.extend(
                value
                for value in field_values
                if isinstance(value, str)
            )

    return _tokens(" ".join(values))


def select_targets(
    instruction: str,
    candidate_files: list[str],
    *,
    max_targets: int = 5,
    repository_map: dict[str, dict] | None = None,
) -> list[str]:
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    instruction_tokens = _tokens(instruction)

    scored = []

    for candidate in candidate_files:
        path = Path(candidate)

        path_tokens = _tokens(
            " ".join(
                [
                    candidate,
                    path.stem,
                    *path.parts,
                ]
            )
        )

        content_tokens = _content_tokens(
            candidate,
            repository_map,
        )

        path_score = len(
            instruction_tokens & path_tokens
        )
        content_score = len(
            instruction_tokens & content_tokens
        )

        total_score = (
            path_score * 3
            + content_score
        )

        if total_score > 0:
            scored.append(
                (
                    -total_score,
                    -path_score,
                    len(path.parts),
                    candidate,
                )
            )

    scored.sort()

    return [
        candidate
        for _, _, _, candidate in scored[:max_targets]
    ]
