from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from v012_inventory import parse_inventory


def expect_value(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label}: expected {expected!r}, got {actual!r}"
        )


def expect_value_error(lines, label):
    try:
        parse_inventory(lines)
    except ValueError:
        return

    raise AssertionError(
        f"{label}: expected ValueError"
    )


expect_value(
    parse_inventory(
        [
            "  Apples : 2 ",
            "apples:3",
            "",
            " # warehouse note",
            "BANANAS: 4",
            " bananas :1",
        ]
    ),
    {
        "apples": 5,
        "bananas": 5,
    },
    "normalization and aggregation",
)

expect_value(
    parse_inventory(
        [
            "\tWidget A\t:10",
            "widget   a:5",
        ]
    ),
    {
        "widget a": 15,
    },
    "internal whitespace normalization",
)

expect_value(
    parse_inventory([]),
    {},
    "empty input",
)

expect_value_error(
    ["missing separator"],
    "missing separator",
)

expect_value_error(
    ["item:not-a-number"],
    "non-integer quantity",
)

expect_value_error(
    ["item:0"],
    "zero quantity",
)

expect_value_error(
    ["item:-3"],
    "negative quantity",
)

expect_value_error(
    [":3"],
    "empty item name",
)

expect_value_error(
    ["item:2:extra"],
    "extra separator",
)

print("V0.12 verification PASS")
