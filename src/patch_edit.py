import json


def parse_patch_response(
    content: str,
    *,
    expected_target: str,
) -> tuple[str, str, str]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "patch response is not valid JSON"
        ) from exc

    if not isinstance(payload, dict) or set(payload) != {"patch"}:
        raise ValueError(
            "patch response must contain only patch"
        )

    patch = payload["patch"]
    if not isinstance(patch, dict):
        raise ValueError("patch must be a JSON object")

    if set(patch) != {"path", "old", "new"}:
        raise ValueError(
            "patch must contain exactly path, old, and new"
        )

    path = patch["path"]
    old = patch["old"]
    new = patch["new"]

    if path != expected_target:
        raise ValueError(
            "patch target mismatch: "
            f"expected {expected_target}, got {path}"
        )

    if not isinstance(old, str) or not old:
        raise ValueError("patch old text must be non-empty")

    if not isinstance(new, str):
        raise ValueError("patch new text must be text")

    return path, old, new


def apply_exact_patch(
    source: str,
    *,
    old: str,
    new: str,
) -> str:
    occurrences = source.count(old)

    if occurrences != 1:
        raise ValueError(
            "patch old text must match exactly once; "
            f"found {occurrences}"
        )

    return source.replace(old, new, 1)
