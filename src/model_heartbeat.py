from pathlib import Path

from builder import FixSimpleBuilder
from local_llama_model import LocalLlamaModel
from model_interface import ModelRequest


REPO = Path(__file__).resolve().parents[1]

BROKEN = """def add(a, b):
    return a - b
"""

VERIFY = """import sys
sys.path.insert(0, "src")

from a0_target import add

result = add(2, 3)

if result != 5:
    raise AssertionError(f"expected 5, got {result}")

print("verification PASS:", result)
"""


def main():
    builder = FixSimpleBuilder(REPO)

    model = LocalLlamaModel(
        "models/granite-4.0-1b-Q4_K_M.gguf"
    )

    builder.write_file("src/a0_target.py", BROKEN)
    builder.write_file("tests/a0_verify.py", VERIFY)

    first = builder.run("python3 -B tests/a0_verify.py")

    print("FIRST ATTEMPT:", "PASS" if first.passed else "FAIL")

    if first.passed:
        raise RuntimeError("Test fixture did not fail as expected.")

    print("Observed failure:")
    print(first.stderr.strip())

    request = ModelRequest(
        task=(
            "Repair src/a0_target.py so that "
            "tests/a0_verify.py passes."
        ),
        context=(
            "CURRENT FILE:\n"
            + builder.read_file("src/a0_target.py")
            + "\n\nVERIFICATION FAILURE:\n"
            + first.stderr
        ),
    )

    print("\nCalling FixSimple Model Interface...")
    response = model.complete(request)

    print("MODEL:", response.model)
    print("MODEL PROPOSED:")
    print(response.content)

    builder.write_file(
        "src/a0_target.py",
        response.content.rstrip() + "\n",
    )

    second = builder.run("python3 -B tests/a0_verify.py")

    print(
        "\nSECOND ATTEMPT:",
        "PASS" if second.passed else "FAIL"
    )

    if second.stdout.strip():
        print(second.stdout.strip())

    if not second.passed:
        print(second.stderr.strip())
        raise RuntimeError("MODEL-DRIVEN A0 FAILED")

    print("\n=== MODEL-DRIVEN EVIDENCE ===")
    print("Initial verification: FAIL")
    print("Repair source: LOCAL MODEL")
    print("Repair iterations: 1")
    print("Final verification: PASS")
    print("Model:", response.model)
    print("\nFinal target:")
    print(builder.read_file("src/a0_target.py"))

    print("A0 MODEL-DRIVEN HEARTBEAT: PASS")


if __name__ == "__main__":
    main()
