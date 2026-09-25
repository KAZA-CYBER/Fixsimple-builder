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


def parse_multi_patch_response(
    content: str,
    *,
    expected_targets: list[str],
) -> list[tuple[str, str, str]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "multi-patch response is not valid JSON"
        ) from exc

    if not isinstance(payload, dict) or set(payload) != {"patches"}:
        raise ValueError(
            "multi-patch response must contain only patches"
        )

    patches = payload["patches"]
    if not isinstance(patches, list) or not patches:
        raise ValueError(
            "multi-patch response patches must be a non-empty list"
        )

    expected = set(expected_targets)
    parsed = []
    returned = []

    for patch in patches:
        if not isinstance(patch, dict):
            raise ValueError("each patch must be a JSON object")

        if set(patch) != {"path", "old", "new"}:
            raise ValueError(
                "each patch must contain exactly path, old, and new"
            )

        path = patch["path"]
        old = patch["old"]
        new = patch["new"]

        if path not in expected:
            raise ValueError(
                "multi-patch target mismatch: unexpected target "
                + str(path)
            )

        if path in returned:
            raise ValueError(
                "multi-patch target duplicated: " + path
            )

        if not isinstance(old, str) or not old:
            raise ValueError(
                "multi-patch old text must be non-empty"
            )

        if not isinstance(new, str):
            raise ValueError(
                "multi-patch new text must be text"
            )

        returned.append(path)
        parsed.append((path, old, new))

    if set(returned) != expected:
        missing = sorted(expected - set(returned))
        extra = sorted(set(returned) - expected)
        raise ValueError(
            "multi-patch target mismatch; "
            f"missing={missing}, extra={extra}"
        )

    return parsed


def plan_multi_patch_writes(
    current_contents: dict[str, str],
    patches: list[tuple[str, str, str]],
) -> dict[str, str]:
    planned = {}

    for path, old, new in patches:
        if path not in current_contents:
            raise ValueError(
                "multi-patch current content missing: " + path
            )

        planned[path] = apply_exact_patch(
            current_contents[path],
            old=old,
            new=new,
        )

    return planned
