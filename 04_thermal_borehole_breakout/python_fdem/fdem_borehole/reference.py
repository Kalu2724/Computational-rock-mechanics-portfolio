"""Reference-data reduction and loading helpers."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from .model import SimulationResult


def build_irazu_radial_profile(source_zip: str | Path, output_csv: str | Path | None = None) -> pd.DataFrame:
    with ZipFile(source_zip) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        with archive.open(name) as stream:
            raw = pd.read_csv(stream, usecols=["Points_Magnitude", "solid temperature", "displacement_Magnitude"])
    radius = raw["Points_Magnitude"].to_numpy()
    edges = np.arange(110.0, 1_010.0, 10.0); index = np.digitize(radius, edges) - 1; records = []
    for i, (lower, upper) in enumerate(zip(edges[:-1], edges[1:])):
        selected = raw.loc[index == i]
        if selected.empty:
            continue
        t = selected["solid temperature"]; u = selected["displacement_Magnitude"]
        records.append({"radius_mm": 0.5 * (lower + upper), "count": len(selected), "temperature_mean_c": t.mean(), "temperature_median_c": t.median(), "temperature_std_c": t.std(), "displacement_mean_mm": u.mean(), "displacement_median_mm": u.median(), "displacement_std_mm": u.std()})
    profile = pd.DataFrame(records)
    if output_csv is not None:
        destination = Path(output_csv); destination.parent.mkdir(parents=True, exist_ok=True); profile.to_csv(destination, index=False)
    return profile


def load_irazu_radial_profile(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_irazu_stress_history(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path).rename(columns={"Time (ms)": "mechanical_time_ms", "stresses magnitude (Pa)": "stress_magnitude_pa"})


def model_radial_profile(result: SimulationResult) -> pd.DataFrame:
    ids = result.mesh.triangles.ravel(); magnitude = np.linalg.norm(result.final_displacement, axis=1)
    total = np.zeros(len(result.mesh.geometric_nodes)); count = np.zeros_like(total)
    np.add.at(total, ids, magnitude); np.add.at(count, ids, 1)
    return pd.DataFrame({"radius_mm": 1e3 * np.linalg.norm(result.mesh.geometric_nodes, axis=1), "temperature_c": result.temperature_solutions[-1], "displacement_mm": 1e3 * total / np.maximum(count, 1)}).sort_values("radius_mm")
