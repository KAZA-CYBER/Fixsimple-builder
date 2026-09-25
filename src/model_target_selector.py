import json

from model_interface import FixSimpleModel, ModelRequest


def _validate_targets(
    selected,
    candidate_files: list[str],
    *,
    max_targets: int,
) -> list[str]:
    if not isinstance(selected, list):
        raise ValueError("model targets must be a list")

    if len(selected) > max_targets:
        raise ValueError(
            "model selected too many targets: "
            f"{len(selected)} > {max_targets}"
        )

    if any(
        not isinstance(target, str) or not target
        for target in selected
    ):
        raise ValueError(
            "model targets must be non-empty strings"
        )

    if len(set(selected)) != len(selected):
        raise ValueError(
            "model targets must be unique"
        )

    candidates = set(candidate_files)
    unknown = [
        target
        for target in selected
        if target not in candidates
    ]
    if unknown:
        raise ValueError(
            "model selected non-candidate targets: "
            + ", ".join(unknown)
        )

    return selected


def select_targets_with_model(
    instruction: str,
    candidate_files: list[str],
    repository_map: dict[str, dict],
    model: FixSimpleModel,
    *,
    max_targets: int = 5,
) -> list[str]:
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    context = json.dumps(
        {
            "candidate_files": candidate_files,
            "repository_map": repository_map,
            "max_targets": max_targets,
        },
        indent=2,
        sort_keys=True,
    )

    response = model.complete(
        ModelRequest(
            task=instruction,
            context=context,
            response_contract="target_selection_json",
        )
    )

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "model target selection returned invalid JSON"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "model target selection must be a JSON object"
        )

    if set(data) != {"targets"}:
        raise ValueError(
            "model target selection must contain only targets"
        )

    return _validate_targets(
        data["targets"],
        candidate_files,
        max_targets=max_targets,
    )
