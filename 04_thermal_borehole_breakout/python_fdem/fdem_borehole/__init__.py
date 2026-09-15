"""Thermo-mechanical FDEM-style borehole reconstruction."""

from .model import ModelConfig, SimulationResult, run_thermal_breakout

__all__ = ["ModelConfig", "SimulationResult", "run_thermal_breakout"]
