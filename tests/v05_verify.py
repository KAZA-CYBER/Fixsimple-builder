import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from v05_text_utils import normalize_text, word_count


cases = [
    (normalize_text("  Hello   WORLD  "), "hello world"),
    (normalize_text("\tFixSimple\n Builder "), "fixsimple builder"),
    (normalize_text("   "), ""),
]

for actual, expected in cases:
    if actual != expected:
        raise AssertionError(
            f"normalize_text expected {expected!r}, got {actual!r}"
        )

word_cases = [
    (word_count("one two three"), 3),
    (word_count("  ONE   two "), 2),
    (word_count(""), 0),
    (word_count("   "), 0),
]

for actual, expected in word_cases:
    if actual != expected:
        raise AssertionError(
            f"word_count expected {expected}, got {actual}"
        )

print("V0.5 verification PASS")
