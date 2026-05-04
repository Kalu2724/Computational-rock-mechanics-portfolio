#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path)

    required_cols = [
        "Time (s)",
        "displacement magnitude (m)",
        "displacement x (m)",
        "displacement y (m)",
        "displacement (polar) r (m)",
        "displacement (polar) θ (m)",
        "force magnitude (N)",
        "velocity magnitude (m/s)",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns in {path.name}: {missing}\n"
            f"Columns found: {list(df.columns)}"
        )

    return df


def make_output_dir(base_dir: Path) -> Path:
    out_dir = base_dir / "tunnel_case_comparison_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_summary(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    summary = pd.DataFrame([
        {
            "Case": "Case 1",
            "Rows": len(case1),
            "Final time (s)": float(case1["Time (s)"].iloc[-1]),
            "Final displacement magnitude (m)": float(case1["displacement magnitude (m)"].iloc[-1]),
            "Final displacement x (m)": float(case1["displacement x (m)"].iloc[-1]),
            "Final displacement y (m)": float(case1["displacement y (m)"].iloc[-1]),
            "Final radial displacement (m)": float(case1["displacement (polar) r (m)"].iloc[-1]),
            "Final tangential displacement (m)": float(case1["displacement (polar) θ (m)"].iloc[-1]),
            "Final velocity magnitude (m/s)": float(case1["velocity magnitude (m/s)"].iloc[-1]),
            "Final force magnitude (N)": float(case1["force magnitude (N)"].iloc[-1]),
        },
        {
            "Case": "Case 2",
            "Rows": len(case2),
            "Final time (s)": float(case2["Time (s)"].iloc[-1]),
            "Final displacement magnitude (m)": float(case2["displacement magnitude (m)"].iloc[-1]),
            "Final displacement x (m)": float(case2["displacement x (m)"].iloc[-1]),
            "Final displacement y (m)": float(case2["displacement y (m)"].iloc[-1]),
            "Final radial displacement (m)": float(case2["displacement (polar) r (m)"].iloc[-1]),
            "Final tangential displacement (m)": float(case2["displacement (polar) θ (m)"].iloc[-1]),
            "Final velocity magnitude (m/s)": float(case2["velocity magnitude (m/s)"].iloc[-1]),
            "Final force magnitude (N)": float(case2["force magnitude (N)"].iloc[-1]),
        }
    ])

    summary_path = out_dir / "tunnel_case_comparison_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Saved summary CSV: {summary_path}")
    return summary


def save_combined(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> Path:
    case1_copy = case1.copy()
    case2_copy = case2.copy()

    case1_copy["Case"] = "Case 1"
    case2_copy["Case"] = "Case 2"

    combined = pd.concat([case1_copy, case2_copy], ignore_index=True)
    combined_path = out_dir / "tunnel_case1_case2_node_selection_comparison.csv"
    combined.to_csv(combined_path, index=False)
    print(f"Saved combined CSV: {combined_path}")
    return combined_path


def plot_displacement_magnitude(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.5))
    plt.plot(case1["Time (s)"], case1["displacement magnitude (m)"], label="Case 1")
    plt.plot(case2["Time (s)"], case2["displacement magnitude (m)"], label="Case 2")
    plt.xlabel("Time (s)")
    plt.ylabel("Displacement magnitude (m)")
    plt.title("Tunnel Excavation: Average Displacement Magnitude Comparison")
    plt.legend()
    plt.grid(True)
    out = out_dir / "tunnel_case1_case2_displacement_magnitude_comparison.png"
    plt.savefig(out, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved plot: {out}")


def plot_polar_displacement(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.5))
    plt.plot(case1["Time (s)"], case1["displacement (polar) r (m)"], label="Case 1 radial")
    plt.plot(case2["Time (s)"], case2["displacement (polar) r (m)"], label="Case 2 radial")
    plt.plot(case1["Time (s)"], case1["displacement (polar) θ (m)"], label="Case 1 tangential")
    plt.plot(case2["Time (s)"], case2["displacement (polar) θ (m)"], label="Case 2 tangential")
    plt.xlabel("Time (s)")
    plt.ylabel("Displacement (m)")
    plt.title("Tunnel Excavation: Polar Displacement Comparison")
    plt.legend()
    plt.grid(True)
    out = out_dir / "tunnel_case1_case2_polar_displacement_comparison.png"
    plt.savefig(out, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved plot: {out}")


def plot_velocity_magnitude(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.5))
    plt.plot(case1["Time (s)"], case1["velocity magnitude (m/s)"], label="Case 1")
    plt.plot(case2["Time (s)"], case2["velocity magnitude (m/s)"], label="Case 2")
    plt.xlabel("Time (s)")
    plt.ylabel("Velocity magnitude (m/s)")
    plt.title("Tunnel Excavation: Average Velocity Magnitude Comparison")
    plt.legend()
    plt.grid(True)
    out = out_dir / "tunnel_case1_case2_velocity_magnitude_comparison.png"
    plt.savefig(out, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved plot: {out}")


def plot_force_magnitude(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.5))
    plt.plot(case1["Time (s)"], case1["force magnitude (N)"], label="Case 1")
    plt.plot(case2["Time (s)"], case2["force magnitude (N)"], label="Case 2")
    plt.xlabel("Time (s)")
    plt.ylabel("Force magnitude (N)")
    plt.title("Tunnel Excavation: Average Force Magnitude Comparison")
    plt.legend()
    plt.grid(True)
    out = out_dir / "tunnel_case1_case2_force_magnitude_comparison.png"
    plt.savefig(out, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved plot: {out}")


def plot_cartesian_displacement(case1: pd.DataFrame, case2: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.5))
    plt.plot(case1["Time (s)"], case1["displacement x (m)"], label="Case 1 x")
    plt.plot(case2["Time (s)"], case2["displacement x (m)"], label="Case 2 x")
    plt.plot(case1["Time (s)"], case1["displacement y (m)"], label="Case 1 y")
    plt.plot(case2["Time (s)"], case2["displacement y (m)"], label="Case 2 y")
    plt.xlabel("Time (s)")
    plt.ylabel("Displacement (m)")
    plt.title("Tunnel Excavation: Cartesian Displacement Comparison")
    plt.legend()
    plt.grid(True)
    out = out_dir / "tunnel_case1_case2_cartesian_displacement_comparison.png"
    plt.savefig(out, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved plot: {out}")


def main() -> None:
    base_dir = Path.cwd()

    case1_file = base_dir / "case1_tunnel_node_selection_history.csv"
    case2_file = base_dir / "case2_tunnel_node_selection_history.csv"

    print("Reading input files...")
    case1 = load_csv(case1_file)
    case2 = load_csv(case2_file)

    out_dir = make_output_dir(base_dir)

    summary = save_summary(case1, case2, out_dir)
    print("\nComparison summary:")
    print(summary.to_string(index=False))

    save_combined(case1, case2, out_dir)

    plot_displacement_magnitude(case1, case2, out_dir)
    plot_polar_displacement(case1, case2, out_dir)
    plot_velocity_magnitude(case1, case2, out_dir)
    plot_force_magnitude(case1, case2, out_dir)
    plot_cartesian_displacement(case1, case2, out_dir)

    print(f"\nAll outputs saved in: {out_dir}")


if __name__ == "__main__":
    main()


# In[ ]:




