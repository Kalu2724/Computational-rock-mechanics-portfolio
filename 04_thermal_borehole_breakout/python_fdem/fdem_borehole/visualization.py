"""Portfolio figures for the thermal-borehole reconstruction."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from .reference import model_radial_profile
from .validation import kirsch_wall_profile

BLUE, ORANGE, PURPLE, DARK, GREY = "#195A7A", "#D97720", "#7B4B94", "#263238", "#7C8A91"


def set_plot_style() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.titlesize": 12, "axes.labelsize": 10.5, "axes.edgecolor": DARK, "axes.grid": True, "grid.color": "#DCE3E7", "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"})


def _compression(stress: np.ndarray) -> np.ndarray:
    tensor = np.zeros((len(stress), 2, 2)); tensor[:, 0, 0] = stress[:, 0]; tensor[:, 1, 1] = stress[:, 1]; tensor[:, 0, 1] = tensor[:, 1, 0] = stress[:, 2]
    return np.maximum(-np.linalg.eigvalsh(tensor)[:, 0], 0) / 1e6


def plot_model_setup(result):
    set_plot_style(); c, m = result.config, result.mesh; fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.7))
    for ax, limit, title in zip(axes, [c.half_domain * 1.04, 0.62], ["10 m × 10 m model domain", "Near-borehole FDEM refinement"]):
        ax.triplot(1e3 * m.geometric_nodes[:, 0], 1e3 * m.geometric_nodes[:, 1], m.triangles, color="#AEBBC2", lw=0.35 if limit < 1 else 0.18)
        ax.add_patch(Circle((0, 0), 1e3 * c.borehole_radius, facecolor="white", edgecolor=DARK, lw=1.5, zorder=5)); ax.set_aspect("equal"); ax.set_xlim(-1e3 * limit, 1e3 * limit); ax.set_ylim(-1e3 * limit, 1e3 * limit); ax.set(xlabel="x (mm)", ylabel="y (mm)", title=title); ax.grid(False)
    axes[0].annotate(r"$\sigma_H=60$ MPa", (0, 4600), ha="center", color=BLUE); axes[0].annotate(r"$\sigma_h=30$ MPa", (4450, 0), ha="right", rotation=90, color=ORANGE)
    axes[1].annotate("$p_m=37$ MPa\n$T_w=140$ °C", (0, 0), ha="center", va="center", fontsize=9)
    fig.suptitle("Thermally loaded borehole: geometry and boundary conditions"); fig.tight_layout(rect=(0, 0, 1, .95)); return fig


def plot_temperature_comparison(result, reference: pd.DataFrame):
    set_plot_style(); c, m = result.config, result.mesh; fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.8))
    field = a.tripcolor(1e3 * m.geometric_nodes[:, 0], 1e3 * m.geometric_nodes[:, 1], m.triangles, result.temperature_solutions[-1], shading="gouraud", cmap="inferno", vmin=c.initial_temperature, vmax=c.wall_temperature)
    a.add_patch(Circle((0, 0), 1e3 * c.borehole_radius, facecolor="white", edgecolor=DARK, lw=1.3)); a.set_aspect("equal"); a.set_xlim(-800, 800); a.set_ylim(-800, 800); a.set(xlabel="x (mm)", ylabel="y (mm)", title="Python temperature field"); a.grid(False); fig.colorbar(field, ax=a).set_label("Solid temperature (°C)")
    radius = reference.radius_mm.to_numpy(); model = model_radial_profile(result).sort_values("radius_mm"); predicted = np.interp(radius, model.radius_mm, model.temperature_c); mean = reference.temperature_mean_c.to_numpy(); std = reference.temperature_std_c.fillna(0).to_numpy()
    b.fill_between(radius, mean - std, mean + std, color=ORANGE, alpha=.16, label="Irazu ±1 standard deviation"); b.plot(radius, mean, color=ORANGE, lw=2, label="Irazu radial mean"); b.plot(radius, predicted, color=BLUE, lw=2.2, label="Python conduction solution"); b.set_xlim(110, 1000); b.set_ylim(38, 145); b.set(xlabel="Radius from borehole centre (mm)", ylabel="Solid temperature (°C)", title="Radial temperature validation"); b.legend(); fig.tight_layout(); return fig


def plot_kirsch_validation(result):
    set_plot_style(); p = kirsch_wall_profile(result); fig, ax = plt.subplots(figsize=(7.5, 4.5)); ax.plot(p.angle_deg, p.kirsch_hoop_compression_mpa, color=DARK, lw=2.1, label="Kirsch solution at element radius"); ax.scatter(p.angle_deg, p.numerical_hoop_compression_mpa, s=12, color=BLUE, alpha=.8, label="Python FDEM before heating"); ax.axhline(0, color=GREY, lw=.9); ax.set_xlim(-180, 180); ax.set(xlabel="Borehole azimuth (degrees)", ylabel="Hoop compression (MPa)", title="Elastic verification before thermal damage"); ax.legend(); fig.tight_layout(); return fig


def _fracture_panel(ax, result, snapshot, limits, threshold):
    m = result.mesh; current = m.nodes + snapshot.displacement; polygons = 1e3 * current[m.element_nodes]; compression = _compression(snapshot.element_stress)
    collection = PolyCollection(polygons, array=compression, cmap="Blues", clim=limits, edgecolors="#D7E0E5", linewidths=.12); ax.add_collection(collection)
    damaged = snapshot.interface_damage >= threshold
    if np.any(damaged):
        segments = 1e3 * .5 * (current[m.face_a[damaged]] + current[m.face_b[damaged]]); mode = snapshot.mode_mixity[damaged]; cmap = LinearSegmentedColormap.from_list("modes", [BLUE, PURPLE, ORANGE]); ax.add_collection(LineCollection(segments, array=mode, cmap=cmap, clim=(0, 1), linewidths=1 + 2.4 * snapshot.interface_damage[damaged], capstyle="round"))
    ax.add_patch(Circle((0, 0), 1e3 * result.config.borehole_radius, facecolor="white", edgecolor=DARK, lw=1.1, zorder=6)); ax.set_aspect("equal"); ax.set_xlim(-350, 350); ax.set_ylim(-350, 350); ax.set_title(snapshot.label); ax.grid(False); return collection


def plot_breakout_evolution(result, damage_threshold=.15):
    set_plot_style(); values = np.concatenate([_compression(s.element_stress) for s in result.snapshots]); limits = (0, float(np.nanpercentile(values, 98))); fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.5), sharex=True, sharey=True)
    collection = None
    for ax, snapshot in zip(axes.ravel()[:5], result.snapshots): collection = _fracture_panel(ax, result, snapshot, limits, damage_threshold)
    axes[1, 2].axis("off"); axes[1, 2].legend(handles=[Line2D([0], [0], color=BLUE, lw=3, label="opening dominated"), Line2D([0], [0], color=PURPLE, lw=3, label="mixed mode"), Line2D([0], [0], color=ORANGE, lw=3, label="shear dominated")], loc="center", title="Cohesive failure mode")
    axes[0, 0].set_ylabel("y (mm)"); axes[1, 0].set_ylabel("y (mm)"); axes[1, 0].set_xlabel("x (mm)"); axes[1, 1].set_xlabel("x (mm)")
    cax = fig.add_axes([.22, .055, .56, .026]); fig.colorbar(collection, cax=cax, orientation="horizontal").set_label("Maximum compressive principal stress (MPa)"); fig.suptitle(f"Thermally induced cohesive localization (interfaces with $D \\geq {damage_threshold:.2f}$)"); fig.subplots_adjust(left=.08, right=.98, top=.92, bottom=.18, hspace=.16, wspace=.12); return fig


def plot_stress_history(result, reference):
    set_plot_style(); model = result.history[result.history.phase == "heating"].drop_duplicates("heating_fraction", keep="last"); rt = reference.mechanical_time_ms.to_numpy(); rs = reference.stress_magnitude_pa.to_numpy() / 1e6; ms = model.monitor_stress_magnitude_mpa.to_numpy()
    normalize = lambda x: (x - x[0]) / max(x[-1] - x[0], 1e-30)
    fig, ax = plt.subplots(figsize=(7.4, 4.5)); ax.plot(rt / rt[-1], normalize(rs), color=ORANGE, marker="o", ms=3, label=f"Irazu: {rs[0]:.1f}→{rs[-1]:.1f} MPa"); ax.plot(model.heating_fraction, normalize(ms), color=BLUE, marker="s", ms=4, label=f"Python probe: {ms[0]:.1f}→{ms[-1]:.1f} MPa"); ax.set_xlim(0, 1); ax.set_ylim(-.12, 1.08); ax.set(xlabel="Normalized heating/loading progress", ylabel="Normalized monitored-stress increase", title="Monitored stress evolution"); ax.legend(loc="lower right"); ax.text(.02, .97, "Normalized because the Irazu probe coordinates were not retained in the export.", transform=ax.transAxes, va="top", fontsize=8.8, color=GREY); fig.tight_layout(); return fig


def plot_damage_and_energy(result):
    set_plot_style(); h = result.history[result.history.phase == "heating"]; fig, (a, b) = plt.subplots(2, 1, figsize=(7.5, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]}); a.plot(h.heating_fraction, h.yielded_interfaces, color=PURPLE, lw=2, label="damaged"); a.plot(h.heating_fraction, h.broken_interfaces, color=ORANGE, lw=2, label="fully failed"); a.set(ylabel="Number of interfaces", title="Damage growth and numerical energy check"); a.legend(); b.semilogy(h.heating_fraction, np.maximum(h.kinetic_to_internal_ratio, 1e-10), color=BLUE, lw=2); b.axhline(.05, color=GREY, ls="--", label="5% guide"); b.set(xlabel="Thermal-time fraction", ylabel="$E_k/E_{int}$"); b.legend(); fig.tight_layout(); return fig


def save_portfolio_figures(result, profile, stress, directory: str | Path) -> Path:
    output = Path(directory); output.mkdir(parents=True, exist_ok=True)
    figures = {"model_setup.png": plot_model_setup(result), "temperature_comparison.png": plot_temperature_comparison(result, profile), "kirsch_validation.png": plot_kirsch_validation(result), "breakout_evolution.png": plot_breakout_evolution(result), "stress_history_comparison.png": plot_stress_history(result, stress), "damage_energy.png": plot_damage_and_energy(result)}
    for name, figure in figures.items(): figure.savefig(output / name, dpi=220, bbox_inches="tight"); plt.close(figure)
    return output
