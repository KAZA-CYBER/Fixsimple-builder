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


def select_targets(
    instruction: str,
    candidate_files: list[str],
    *,
    max_targets: int = 5,
) -> list[str]:
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    instruction_tokens = _tokens(instruction)

    scored = []

    for candidate in candidate_files:
        path = Path(candidate)

        candidate_tokens = _tokens(
            " ".join(
                [
                    candidate,
                    path.stem,
                    *path.parts,
                ]
            )
        )

        score = len(
            instruction_tokens & candidate_tokens
        )

        if score > 0:
            scored.append(
                (
                    -score,
                    len(path.parts),
                    candidate,
                )
            )

    scored.sort()

    return [
        candidate
        for _, _, candidate in scored[:max_targets]
    ]
