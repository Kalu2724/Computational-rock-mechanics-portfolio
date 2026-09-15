"""Mechanical verification checks and comparison metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .model import (
    ModelConfig,
    SimulationResult,
    _softening_function,
    build_mesh,
    bulk_response,
    cohesive_response,
    initialize_interfaces,
    precompute_elements,
)


def run_mechanical_checks(config: ModelConfig | None = None) -> pd.DataFrame:
    """Run small deterministic tests without a full UCS simulation."""
    config = config or ModelConfig()
    mesh = build_mesh(config)
    elements = precompute_elements(mesh, config)
    checks: list[dict[str, object]] = []

    area_error = abs(elements.area.sum() - config.width * config.height)
    checks.append(
        {
            "check": "mesh area",
            "measured": area_error,
            "tolerance": 1.0e-12,
            "passed": area_error < 1.0e-12,
        }
    )
    expected_mass = config.density * config.width * config.height * config.thickness
    mass_error = abs(elements.mass.sum() - expected_mass)
    checks.append(
        {
            "check": "lumped mass",
            "measured": mass_error,
            "tolerance": 1.0e-12,
            "passed": mass_error < 1.0e-12,
        }
    )

    angle = 0.37
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    )
    rigid_displacement = mesh.nodes @ rotation.T - mesh.nodes + np.array([0.002, -0.001])
    rigid_force, rigid_stress, rigid_energy = bulk_response(mesh, elements, rigid_displacement)
    rigid_measure = max(float(np.abs(rigid_force).max()), float(np.abs(rigid_stress).max()), rigid_energy)
    checks.append(
        {
            "check": "rigid-body objectivity",
            "measured": rigid_measure,
            "tolerance": 1.0e-3,
            "passed": rigid_measure < 1.0e-3,
        }
    )

    affine_gradient = np.array([[1.0e-4, 2.0e-5], [2.0e-5, -2.0e-4]])
    affine_displacement = mesh.nodes @ affine_gradient.T
    bulk_force, stress, _ = bulk_response(mesh, elements, affine_displacement)
    expected_strain = np.array([1.0e-4, -2.0e-4, 4.0e-5])
    expected_stress = elements.D @ expected_strain
    patch_error = float(np.max(np.abs(stress - expected_stress)))
    checks.append(
        {
            "check": "constant-strain patch",
            "measured": patch_error,
            "tolerance": 1.0e-2,
            "passed": patch_error < 1.0e-2,
        }
    )

    rng = np.random.default_rng(4)
    trial_displacement = 1.0e-9 * rng.normal(size=mesh.nodes.shape)
    state = initialize_interfaces(mesh, config)
    interface_force, _, _, _ = cohesive_response(mesh, config, state, trial_displacement)
    balance_error = float(np.linalg.norm(interface_force.sum(axis=0)))
    checks.append(
        {
            "check": "cohesive action-reaction",
            "measured": balance_error,
            "tolerance": 1.0e-10,
            "passed": balance_error < 1.0e-10,
        }
    )

    damage = np.linspace(0.0, 1.0, 101)
    softening = _softening_function(damage)
    softening_error = max(
        abs(float(softening[0]) - 1.0),
        abs(float(softening[-1])),
        max(float(np.diff(softening).max()), 0.0),
    )
    checks.append(
        {
            "check": "softening endpoints/monotonicity",
            "measured": softening_error,
            "tolerance": 1.0e-12,
            "passed": softening_error < 1.0e-12,
        }
    )
    return pd.DataFrame(checks)


def comparison_metrics(result: SimulationResult, reference: pd.DataFrame) -> pd.Series:
    """Quantify agreement without hiding differences between the solvers."""
    history = result.history.sort_values("axial_strain_percent")
    ref = reference.sort_values("axial_strain_percent")
    max_common_strain = min(
        float(history["axial_strain_percent"].max()),
        float(ref["axial_strain_percent"].max()),
    )
    ref_common = ref[ref["axial_strain_percent"] <= max_common_strain]
    interpolated = np.interp(
        ref_common["axial_strain_percent"],
        history["axial_strain_percent"],
        history["axial_stress_mpa"],
    )
    rmse = float(np.sqrt(np.mean((interpolated - ref_common["axial_stress_mpa"]) ** 2)))
    reference_peak = float(ref["axial_stress_mpa"].max())
    peak_error = 100.0 * (result.peak_ucs_mpa - reference_peak) / reference_peak

    prepeak = history.loc[: history["axial_stress_mpa"].idxmax()]
    elastic = prepeak[
        (prepeak["axial_stress_mpa"] >= 5.0)
        & (prepeak["axial_stress_mpa"] <= 25.0)
    ]
    apparent_modulus = float("nan")
    if len(elastic) >= 3:
        apparent_modulus = float(
            np.polyfit(elastic["axial_strain"], elastic["axial_stress_mpa"], 1)[0] / 1000.0
        )
    quasi_static_ratio = float(prepeak["kinetic_to_internal_ratio"].median())
    return pd.Series(
        {
            "python_peak_ucs_mpa": result.peak_ucs_mpa,
            "irazu_peak_ucs_mpa": reference_peak,
            "peak_error_percent": peak_error,
            "curve_rmse_mpa": rmse,
            "apparent_prepeak_modulus_gpa": apparent_modulus,
            "median_prepeak_kinetic_internal_ratio": quasi_static_ratio,
        },
        name="value",
    )
