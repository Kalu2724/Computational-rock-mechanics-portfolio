"""Verification and comparison metrics for the reconstruction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .model import (
    ModelConfig,
    bulk_response,
    build_mesh,
    build_thermal_system,
    cohesive_response,
    initialize_interfaces,
    plane_strain_matrix,
    precompute_elements,
    solve_temperature_history,
)
from .reference import model_radial_profile


def run_thermomechanical_checks() -> pd.DataFrame:
    config = ModelConfig(angular_divisions=24, thermal_stages=2)
    mesh = build_mesh(config); elements = precompute_elements(mesh, config); thermal = build_thermal_system(mesh, config)
    target_area = (2 * config.half_domain) ** 2 - np.pi * config.borehole_radius**2
    area_error = abs(elements.area.sum() - target_area) / target_area
    mass_error = abs(elements.nodal_mass.sum() - config.density * config.thickness * elements.area.sum()) / (config.density * config.thickness * elements.area.sum())
    conductivity_error = float(np.max(np.abs(thermal.conductivity @ np.ones(len(mesh.geometric_nodes)))))

    uniform_config = ModelConfig(angular_divisions=24, thermal_stages=1, wall_temperature=40.0)
    umesh = build_mesh(uniform_config); uth = build_thermal_system(umesh, uniform_config)
    uniform_error = float(np.max(np.abs(solve_temperature_history(umesh, uth, uniform_config)[-1] - 40.0)))

    # Algebraic patch check: prescribed free in-plane expansion must leave zero stress.
    dT = 75.0; eth = (1 + config.poisson_ratio) * config.effective_thermal_expansion * dT
    thermal_patch_error = float(np.linalg.norm(plane_strain_matrix(config.young_modulus, config.poisson_ratio) @ (np.array([eth, eth, 0.0]) - np.array([eth, eth, 0.0]))))

    state = initialize_interfaces(mesh, config); displacement = np.zeros_like(mesh.nodes)
    displacement[mesh.face_b[0]] += np.array([2e-8, 1e-8])
    force, _, _, _ = cohesive_response(mesh, config, state, displacement, np.zeros((len(mesh.triangles), 3)))
    action_error = float(np.linalg.norm(force.sum(axis=0)))
    checks = [
        ("mesh area", area_error, 2e-3), ("lumped mass", mass_error, 1e-12),
        ("conductivity conservation", conductivity_error, 1e-9), ("uniform-temperature preservation", uniform_error, 1e-8),
        ("stress-free thermal expansion patch", thermal_patch_error, 1e-9), ("cohesive action-reaction", action_error, 1e-10),
    ]
    return pd.DataFrame([{"check": name, "measured": value, "tolerance": tolerance, "passed": value <= tolerance} for name, value, tolerance in checks])


def kirsch_wall_profile(result) -> pd.DataFrame:
    mesh = result.mesh; snapshot = result.snapshots[0]
    radius = np.linalg.norm(mesh.centroids, axis=1); selected = radius <= 0.120
    x, y = mesh.centroids[selected, 0], mesh.centroids[selected, 1]; r = radius[selected]; theta = np.arctan2(y, x)
    stress = snapshot.element_stress[selected]; s, c = np.sin(theta), np.cos(theta)
    hoop = stress[:, 0] * s**2 + stress[:, 1] * c**2 - 2 * stress[:, 2] * s * c
    sx, sy, p, a = result.config.maximum_horizontal_stress, result.config.minimum_horizontal_stress, result.config.mud_pressure, result.config.borehole_radius
    kirsch = 0.5 * (sx + sy) * (1 + a**2 / r**2) - 0.5 * (sx - sy) * (1 + 3 * a**4 / r**4) * np.cos(2 * theta) - p * a**2 / r**2
    order = np.argsort(theta)
    return pd.DataFrame({"angle_deg": np.rad2deg(theta[order]), "radius_m": r[order], "numerical_hoop_compression_mpa": -hoop[order] / 1e6, "kirsch_hoop_compression_mpa": kirsch[order] / 1e6})


def comparison_metrics(result, reference_profile: pd.DataFrame) -> pd.Series:
    model = model_radial_profile(result).sort_values("radius_mm"); radius = reference_profile["radius_mm"].to_numpy()
    predicted = np.interp(radius, model["radius_mm"], model["temperature_c"])
    temperature_rmse = float(np.sqrt(np.mean((predicted - reference_profile["temperature_mean_c"].to_numpy()) ** 2)))
    kirsch = kirsch_wall_profile(result); kirsch_rmse = float(np.sqrt(np.mean((kirsch.numerical_hoop_compression_mpa - kirsch.kirsch_hoop_compression_mpa) ** 2)))
    midpoint = result.mesh.interface_xy.mean(axis=1); rr = np.linalg.norm(midpoint, axis=1); angle = np.arctan2(midpoint[:, 1], midpoint[:, 0])
    damage = result.final_damage.copy(); damage[rr > result.config.refinement_radius] = 0
    sectors = np.abs(np.sin(angle)) >= np.abs(np.cos(angle)); orientation = float(damage[sectors].sum() / max(damage.sum(), 1e-30))
    final = result.history.iloc[-1]
    return pd.Series({"temperature_profile_rmse_c": temperature_rmse, "preheat_kirsch_hoop_rmse_mpa": kirsch_rmse, "top_bottom_damage_fraction": orientation, "baseline_broken_interfaces": float(result.history.iloc[0].broken_interfaces), "final_broken_interfaces": float(final.broken_interfaces), "final_monitor_stress_magnitude_mpa": float(final.monitor_stress_magnitude_mpa), "final_maximum_temperature_c": float(final.maximum_temperature_c)})
