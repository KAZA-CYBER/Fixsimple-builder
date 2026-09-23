import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from v03_target import multiply

result = multiply(4, 3)
if result != 12:
    raise AssertionError(f'expected 12, got {result}')
print('V0.3 verification PASS:', result)
