from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fdem_borehole.validation import run_thermomechanical_checks

checks = run_thermomechanical_checks()
print(checks.to_string(index=False))
assert checks.passed.all()
