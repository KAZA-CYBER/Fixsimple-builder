#!/usr/bin/env python3

from pathlib import Path
from builder import FixSimpleBuilder


BROKEN = """def add(a, b):
    return a - b
"""

REPAIRED = """def add(a, b):
    return a + b
"""

VERIFY_SCRIPT = """\
import sys
sys.path.insert(0, "src")

from a0_target import add

result = add(2, 3)

if result != 5:
    raise AssertionError(f"expected 5, got {result}")

print("verification PASS")
"""


def main():
    repo = Path.cwd()
    builder = FixSimpleBuilder(repo)

    print("=== A0 EXECUTION LOOP ===")
    print("Task: make add(2, 3) return 5")

    builder.write_file("src/a0_target.py", BROKEN)
    builder.write_file("tests/a0_verify.py", VERIFY_SCRIPT)

    first = builder.run("python3 -B tests/a0_verify.py")

    print()
    print("FIRST ATTEMPT:", "PASS" if first.passed else "FAIL")

    if first.passed:
        raise RuntimeError("Initial verification should have failed.")

    print("Observed failure:")
    print(first.stderr.strip())

    print()
    print("Repair iteration: 1")
    builder.write_file("src/a0_target.py", REPAIRED)

    second = builder.run("python3 -B tests/a0_verify.py")

    print("SECOND ATTEMPT:", "PASS" if second.passed else "FAIL")

    if not second.passed:
        print(second.stdout)
        print(second.stderr)
        raise SystemExit(1)

    print()
    print("=== EVIDENCE ===")
    print("Initial verification: FAIL")
    print("Repair iteration: 1")
    print("Final verification: PASS")
    print()
    print("Final target:")
    print(builder.read_file("src/a0_target.py"))

    print("A0 EXECUTION LOOP: PASS")


if __name__ == "__main__":
    main()
