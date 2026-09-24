import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from v04_target import subtract


result = subtract(10, 3)

if result != 7:
    raise AssertionError(
        f"expected 7, got {result}"
    )

print("V0.4 verification PASS:", result)
