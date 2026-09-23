from pathlib import Path

from local_llama_model import LocalLlamaModel
from task_contract import BuilderTask
from task_executor import TaskExecutor


REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / "models/granite-4.0-1b-Q4_K_M.gguf"

TARGET = REPO / "src/v03_target.py"
VERIFY = REPO / "tests/v03_verify.py"

TARGET.write_text(
    "def multiply(a, b):\n"
    "    return a + b\n"
)

VERIFY.write_text(
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n"
    "from v03_target import multiply\n\n"
    "result = multiply(4, 3)\n"
    "if result != 12:\n"
    "    raise AssertionError(f'expected 12, got {result}')\n"
    "print('V0.3 verification PASS:', result)\n"
)

task = BuilderTask(
    task_id="V0.3-LOCAL-MODEL-001",
    instruction=(
        "Repair src/v03_target.py so that "
        "tests/v03_verify.py passes. "
        "Return only the complete corrected Python source file."
    ),
    target_files=["src/v03_target.py"],
    verification_command="python3 -B tests/v03_verify.py",
    max_repair_iterations=2,
)

model = LocalLlamaModel(str(MODEL))
executor = TaskExecutor(REPO, model)

print("=== V0.3 REAL LOCAL MODEL ===")
result = executor.execute(task)

print("Task:", result.task_id)
print("Passed:", result.passed)
print("Repair attempts:", result.attempts)
print("Verification:")
print(result.final_verification_output.strip())

print()
print("=== FINAL TARGET ===")
print(TARGET.read_text())

if not result.passed:
    raise SystemExit(1)

print("V0.3 GENERAL BUILDER + LOCAL MODEL: PASS")
