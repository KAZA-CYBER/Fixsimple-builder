from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from v013_math import add
from v013_format import format_total


assert add(7, 5) == 12
assert add(-2, 3) == 1

assert format_total(12) == "Total: 12"
assert format_total(0) == "Total: 0"
assert format_total(-4) == "Total: -4"

print("V0.13 verification PASS")
