import json
from pathlib import Path


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(
        path.name + ".tmp"
    )

    temp_path.write_text(
        json.dumps(data, indent=2) + "\n"
    )

    temp_path.replace(path)
