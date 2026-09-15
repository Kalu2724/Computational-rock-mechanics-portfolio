"""Run with: python tests/test_mechanics.py"""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from fdem_ucs.validation import run_mechanical_checks


if __name__ == "__main__":
    checks = run_mechanical_checks()
    print(checks.to_string(index=False))
    if not bool(checks["passed"].all()):
        raise SystemExit("One or more mechanical checks failed.")
