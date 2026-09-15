"""Publication-style plots for the UCS FDEM result."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from .model import ModelConfig, SimulationResult, Snapshot


BLUE = "#1F5A7A"
ORANGE = "#D97925"
PURPLE = "#7A4E9D"
DARK = "#263238"
GRID = "#D8E0E5"


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.edgecolor": DARK,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def load_irazu_reference(path: str | Path) -> pd.DataFrame:
    reference = pd.read_csv(path)
    return reference.rename(
        columns={
            "Strain from platen (%)": "axial_strain_percent",
            "Stress (MPa)": "axial_stress_mpa",
            "Average platen force (kN)": "mean_platen_force_kn",
            "Time Step": "step",
        }
    )


def plot_model_setup(result: SimulationResult) -> plt.Figure:
    """Show the irregular mesh, cohesive topology and platen kinematics."""
    set_plot_style()
    mesh, config = result.mesh, result.config
    fig, ax = plt.subplots(figsize=(5.8, 7.2))
    triangles_mm = 1.0e3 * mesh.geometric_nodes[mesh.triangles]
    collection = PolyCollection(
        triangles_mm,
        facecolors="#EEF3F6",
        edgecolors="#8195A1",
        linewidths=0.45,
    )
    ax.add_collection(collection)
    half_overhang = 0.5 * (config.platen_width - config.width)
    for y in (-config.platen_thickness, config.height):
        rectangle = plt.Rectangle(
            (-1.0e3 * half_overhang, 1.0e3 * y),
            1.0e3 * config.platen_width,
            1.0e3 * config.platen_thickness,
            facecolor="#AEB9BF",
            edgecolor=DARK,
            linewidth=1.0,
        )
        ax.add_patch(rectangle)
    arrow = dict(width=0.7, head_width=2.8, head_length=3.0, color=ORANGE, length_includes_head=True)
    ax.arrow(25.0, 112.0, 0.0, -8.0, **arrow)
    ax.arrow(25.0, -12.0, 0.0, 8.0, **arrow)
    ax.text(28.0, 109.0, "$v_p=0.075$ m/s", color=ORANGE, va="center")
    ax.text(28.0, -9.0, "$v_p=0.075$ m/s", color=ORANGE, va="center")
    ax.set(
        xlim=(-9.0, 67.0),
        ylim=(-15.0, 115.0),
        xlabel="x (mm)",
        ylabel="y (mm)",
        title=f"UCS model: {mesh.element_nodes.shape[0]} CST elements and {mesh.face_a.shape[0]} cohesive interfaces",
    )
    ax.set_aspect("equal")
    ax.grid(False)
    fig.tight_layout()
    return fig


def plot_response_comparison(result: SimulationResult, reference: pd.DataFrame) -> plt.Figure:
    """Compare the Python result with the original Irazu history."""
    set_plot_style()
    history = result.history
    peak_python = result.peak_row
    peak_irazu = reference.loc[reference["axial_stress_mpa"].idxmax()]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.plot(
        reference["axial_strain_percent"],
        reference["axial_stress_mpa"],
        color="#7C8A91",
        lw=2.0,
        label="Irazu assignment",
    )
    ax.plot(
        history["axial_strain_percent"],
        history["axial_stress_mpa"],
        color=BLUE,
        lw=2.2,
        label="Python FDEM",
    )
    ax.scatter(peak_irazu["axial_strain_percent"], peak_irazu["axial_stress_mpa"], s=38, color=ORANGE, zorder=4)
    ax.scatter(peak_python["axial_strain_percent"], peak_python["axial_stress_mpa"], s=38, color=BLUE, zorder=4)
    ax.annotate(
        f"Irazu: {peak_irazu['axial_stress_mpa']:.2f} MPa",
        (peak_irazu["axial_strain_percent"], peak_irazu["axial_stress_mpa"]),
        xytext=(8, 13),
        textcoords="offset points",
        color=ORANGE,
    )
    ax.annotate(
        f"Python: {peak_python['axial_stress_mpa']:.2f} MPa",
        (peak_python["axial_strain_percent"], peak_python["axial_stress_mpa"]),
        xytext=(8, -18),
        textcoords="offset points",
        color=BLUE,
    )
    ax.set(
        xlabel="Axial strain (%)",
        ylabel="Axial stress (MPa)",
        title="Global UCS response",
    )
    ax.set_xlim(left=0.0)
    ax.set_ylim(bottom=0.0)
    ax.grid(True)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def select_stage_snapshots(result: SimulationResult) -> tuple[list[Snapshot], list[str]]:
    history = result.history.reset_index(drop=True)
    peak_index = int(history["axial_stress_mpa"].idxmax())
    peak_stress = float(history.loc[peak_index, "axial_stress_mpa"])
    pre = int(np.argmin(np.abs(history.loc[:peak_index, "axial_stress_mpa"].to_numpy() - 0.80 * peak_stress)))
    first_broken = history.index[history["broken_interfaces"] > 0]
    rupture = int(first_broken[0]) if len(first_broken) else peak_index
    post = len(history) - 1
    indices = [pre, rupture, post]
    labels = ["80% of peak", "first complete interface failure", "post-peak localization"]
    return [result.snapshots[i] for i in indices], labels


def _fracture_axis(
    ax: plt.Axes,
    result: SimulationResult,
    snapshot: Snapshot,
    label: str,
    stress_limits: tuple[float, float],
    damage_threshold: float,
) -> PolyCollection:
    mesh = result.mesh
    current_nodes = mesh.nodes + snapshot.displacement
    polygons = 1.0e3 * current_nodes[mesh.element_nodes]
    compression = -snapshot.element_stress[:, 1] / 1.0e6
    collection = PolyCollection(
        polygons,
        array=compression,
        cmap="Blues",
        clim=stress_limits,
        edgecolors="#D7E0E5",
        linewidths=0.15,
    )
    ax.add_collection(collection)

    damaged = snapshot.interface_damage >= damage_threshold
    if np.any(damaged):
        face_a = current_nodes[mesh.face_a[damaged]]
        face_b = current_nodes[mesh.face_b[damaged]]
        segments = 1.0e3 * 0.5 * (face_a + face_b)
        mixity = snapshot.mode_mixity[damaged]
        crack_cmap = LinearSegmentedColormap.from_list("fracture_mode", [BLUE, PURPLE, ORANGE])
        cracks = LineCollection(
            segments,
            array=mixity,
            cmap=crack_cmap,
            clim=(0.0, 1.0),
            linewidths=1.2 + 2.8 * snapshot.interface_damage[damaged],
            capstyle="round",
        )
        ax.add_collection(cracks)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set(xlabel="x (mm)", title=f"{label}\n$\\varepsilon_a$ = {100.0*snapshot.axial_strain:.3f}%")
    ax.grid(False)
    return collection


def plot_fracture_evolution(result: SimulationResult, damage_threshold: float = 0.65) -> plt.Figure:
    """Show stress and localized cracks at pre-peak, peak and post-peak stages."""
    set_plot_style()
    snapshots, labels = select_stage_snapshots(result)
    all_compression = np.concatenate([-s.element_stress[:, 1] / 1.0e6 for s in snapshots])
    limits = (float(np.nanpercentile(all_compression, 2)), float(np.nanpercentile(all_compression, 98)))
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 7.0), sharey=True)
    collection = None
    for ax, snapshot, label in zip(axes, snapshots, labels):
        collection = _fracture_axis(ax, result, snapshot, label, limits, damage_threshold)
    axes[0].set_ylabel("y (mm)")
    assert collection is not None
    cbar = fig.colorbar(collection, ax=axes, orientation="horizontal", fraction=0.045, pad=0.09)
    cbar.set_label("Axial compressive stress, $-\\sigma_{yy}$ (MPa)")
    legend = [
        Line2D([0], [0], color=BLUE, lw=3, label="opening dominated"),
        Line2D([0], [0], color=PURPLE, lw=3, label="mixed mode"),
        Line2D([0], [0], color=ORANGE, lw=3, label="shear dominated"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle(f"Damage localization (interfaces with $D \\geq {damage_threshold:.2f}$)", y=0.98)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.18, wspace=0.18)
    return fig


def plot_energy_balance(result: SimulationResult) -> plt.Figure:
    """Plot energy components and the quasi-static kinetic-energy check."""
    set_plot_style()
    h = result.history
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.4, 6.4), sharex=True, gridspec_kw={"height_ratios": [2.0, 1.0]})
    x = h["axial_strain_percent"]
    ax1.plot(x, h["external_work_j"], color=DARK, lw=2.0, label="external work")
    ax1.plot(x, h["bulk_strain_energy_j"], color=BLUE, lw=1.8, label="bulk strain energy")
    ax1.plot(x, h["fracture_dissipation_j"], color=ORANGE, lw=1.8, label="fracture dissipation")
    ax1.plot(x, h["kinetic_energy_j"], color=PURPLE, lw=1.5, label="kinetic energy")
    ax1.set(ylabel="Energy (J)", title="Numerical energy audit")
    ax1.grid(True)
    ax1.legend(ncol=2)
    ax2.semilogy(x, np.maximum(h["kinetic_to_internal_ratio"], 1.0e-8), color=PURPLE, lw=1.8)
    ax2.axhline(0.05, color="#7C8A91", lw=1.0, ls="--", label="5% guide")
    ax2.set(xlabel="Axial strain (%)", ylabel="$E_k/E_{int}$")
    ax2.grid(True, which="both")
    ax2.legend()
    fig.tight_layout()
    return fig


def save_portfolio_figures(
    result: SimulationResult,
    reference_csv: str | Path,
    output_directory: str | Path,
) -> Path:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    reference = load_irazu_reference(reference_csv)
    figures = {
        "model_setup.png": plot_model_setup(result),
        "stress_strain_comparison.png": plot_response_comparison(result, reference),
        "fracture_evolution.png": plot_fracture_evolution(result),
        "energy_balance.png": plot_energy_balance(result),
    }
    for name, figure in figures.items():
        figure.savefig(output / name, dpi=240, bbox_inches="tight")
        plt.close(figure)
    return output
