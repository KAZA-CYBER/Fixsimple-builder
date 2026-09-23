import sys
sys.path.insert(0, "src")

from a0_target import add

result = add(2, 3)

if result != 5:
    raise AssertionError(f"expected 5, got {result}")

print("verification PASS:", result)
