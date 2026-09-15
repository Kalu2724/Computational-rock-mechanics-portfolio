"""Run the UCS model, verification checks and portfolio plots."""

from __future__ import annotations

import argparse
from pathlib import Path

from fdem_ucs import ModelConfig, run_ucs
from fdem_ucs.model import save_result_data
from fdem_ucs.validation import comparison_metrics, run_mechanical_checks
from fdem_ucs.visualization import load_irazu_reference, save_portfolio_figures


ROOT = Path(__file__).resolve().parent
REFERENCE_CSV = ROOT.parent / "data" / "stress_strain data.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "default_run")
    parser.add_argument("--seed", type=int, default=ModelConfig.random_seed)
    parser.add_argument("--strength-scale", type=float, default=ModelConfig.interface_strength_scale)
    parser.add_argument("--target-strain", type=float, default=ModelConfig.target_axial_strain)
    parser.add_argument("--output-interval", type=int, default=ModelConfig.output_interval)
    args = parser.parse_args()

    checks = run_mechanical_checks()
    print("\nMechanical checks")
    print(checks.to_string(index=False))
    if not bool(checks["passed"].all()):
        raise SystemExit("Mechanical checks failed; simulation not started.")

    config = ModelConfig(
        random_seed=args.seed,
        interface_strength_scale=args.strength_scale,
        target_axial_strain=args.target_strain,
        output_interval=args.output_interval,
    )
    result = run_ucs(config)
    save_result_data(result, args.output)
    save_portfolio_figures(result, REFERENCE_CSV, args.output)
    reference = load_irazu_reference(REFERENCE_CSV)
    metrics = comparison_metrics(result, reference)
    metrics.to_csv(args.output / "comparison_metrics.csv", header=True)
    checks.to_csv(args.output / "mechanical_checks.csv", index=False)
    print("\nComparison metrics")
    print(metrics.to_string())
    print(f"\nSaved results to {args.output.resolve()}")


if __name__ == "__main__":
    main()

