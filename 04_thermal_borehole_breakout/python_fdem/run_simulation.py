"""Run the thermal-borehole reconstruction and save validation outputs."""

from pathlib import Path

from fdem_borehole import ModelConfig, run_thermal_breakout
from fdem_borehole.model import save_result_data
from fdem_borehole.reference import load_irazu_radial_profile, load_irazu_stress_history
from fdem_borehole.validation import comparison_metrics, kirsch_wall_profile, run_thermomechanical_checks
from fdem_borehole.visualization import save_portfolio_figures

ROOT = Path(__file__).resolve().parent


def main() -> None:
    checks = run_thermomechanical_checks(); print(checks.to_string(index=False))
    if not checks.passed.all(): raise SystemExit("A verification check failed")
    result = run_thermal_breakout(ModelConfig())
    profile = load_irazu_radial_profile(ROOT / "data" / "irazu_radial_profile.csv")
    stress = load_irazu_stress_history(ROOT.parent / "data" / "Plot_3.csv")
    output = ROOT / "results" / "default_run"; save_result_data(result, output); save_portfolio_figures(result, profile, stress, output)
    checks.to_csv(output / "thermomechanical_checks.csv", index=False); comparison_metrics(result, profile).to_csv(output / "comparison_metrics.csv", header=True); kirsch_wall_profile(result).to_csv(output / "kirsch_wall_profile.csv", index=False)
    print(f"Saved results to {output}")


if __name__ == "__main__": main()
