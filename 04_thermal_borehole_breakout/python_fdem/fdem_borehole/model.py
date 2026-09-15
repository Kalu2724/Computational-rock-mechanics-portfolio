"""Inspectable 2-D thermo-mechanical FDEM-style borehole model (SI units)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import bmat, coo_matrix, csr_matrix, diags
from scipy.sparse.linalg import spsolve


@dataclass(frozen=True)
class ModelConfig:
    borehole_radius: float = 0.110
    half_domain: float = 5.0
    refinement_radius: float = 0.50
    thickness: float = 1.0
    angular_divisions: int = 72
    maximum_horizontal_stress: float = 60.0e6
    minimum_horizontal_stress: float = 30.0e6
    mud_pressure: float = 37.0e6
    density: float = 2500.0
    young_modulus: float = 60.0e9
    poisson_ratio: float = 0.30
    tensile_strength: float = 7.0e6
    cohesion: float = 60.0e6
    friction_coefficient: float = 0.577
    mode_i_fracture_energy: float = 20.0
    mode_ii_fracture_energy: float = 200.0
    specific_heat_capacity: float = 850.0
    thermal_conductivity: float = 2.5
    initial_temperature: float = 40.0
    wall_temperature: float = 140.0
    reported_thermal_expansion: float = 1.0e-3
    # Explicitly calibrated reduced coupling; see README and sensitivity table.
    effective_thermal_expansion: float = 1.50e-5
    thermal_duration_seconds: float = 6_000.0
    thermal_stages: int = 12
    interface_strength_scale: float = 0.85
    strength_cov: float = 0.08
    random_seed: int = 19
    fracture_penalty_factor: float = 300.0
    dynamic_mass_scale: float = 10.0
    cfl_safety: float = 0.20
    damping_ratio: float = 0.75
    damping_length_scale: float = 0.10
    prestress_relax_steps: int = 600
    steps_per_thermal_stage: int = 900
    output_interval: int = 300

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def friction_angle_deg(self) -> float:
        return float(np.rad2deg(np.arctan(self.friction_coefficient)))


@dataclass
class Mesh:
    geometric_nodes: np.ndarray
    triangles: np.ndarray
    nodes: np.ndarray
    element_nodes: np.ndarray
    centroids: np.ndarray
    face_a: np.ndarray
    face_b: np.ndarray
    interface_xy: np.ndarray
    normal: np.ndarray
    interface_length: np.ndarray
    owner_a: np.ndarray
    owner_b: np.ndarray
    boundary_face_nodes: np.ndarray
    boundary_length: np.ndarray
    boundary_normal: np.ndarray
    boundary_kind: np.ndarray
    inner_geometric_nodes: np.ndarray
    outer_geometric_nodes: np.ndarray
    monitor_element: int


@dataclass
class Elements:
    B: np.ndarray
    D: np.ndarray
    area: np.ndarray
    nodal_mass: np.ndarray
    characteristic_length: np.ndarray
    inverse_reference_jacobian: np.ndarray


@dataclass
class ThermalSystem:
    capacity: np.ndarray
    conductivity: csr_matrix


@dataclass
class InterfaceState:
    damage: np.ndarray
    maximum_opening: np.ndarray
    maximum_slip: np.ndarray
    tensile_strength: np.ndarray
    cohesion: np.ndarray
    mode_mixity: np.ndarray
    activated: np.ndarray
    fracture_dissipation: np.ndarray


@dataclass
class Snapshot:
    step: int
    label: str
    heating_fraction: float
    thermal_time_seconds: float
    temperature: np.ndarray
    displacement: np.ndarray
    element_stress: np.ndarray
    interface_damage: np.ndarray
    mode_mixity: np.ndarray


@dataclass
class SimulationResult:
    config: ModelConfig
    mesh: Mesh
    elements: Elements
    history: pd.DataFrame
    snapshots: list[Snapshot]
    temperature_solutions: list[np.ndarray]
    final_displacement: np.ndarray
    final_velocity: np.ndarray
    final_stress: np.ndarray
    final_damage: np.ndarray
    final_mode_mixity: np.ndarray
    time_step: float
    steps_completed: int
    termination_reason: str


def plane_strain_matrix(E: float, nu: float) -> np.ndarray:
    factor = E / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return factor * np.array(
        [[1.0 - nu, nu, 0.0], [nu, 1.0 - nu, 0.0], [0.0, 0.0, 0.5 * (1.0 - 2.0 * nu)]]
    )


def _radial_coordinates(config: ModelConfig, theta: np.ndarray) -> np.ndarray:
    near = np.array([0.110, 0.120, 0.135, 0.155, 0.180, 0.220, 0.280, 0.360, 0.500])
    if not np.isclose(config.borehole_radius, near[0]):
        scale = config.borehole_radius / near[0]
        near = config.borehole_radius + (near - near[0]) * scale
    outer = config.half_domain / np.maximum(np.abs(np.cos(theta)), np.abs(np.sin(theta)))
    fractions = np.array([0.04, 0.09, 0.16, 0.26, 0.40, 0.57, 0.76, 1.0])
    rings = [np.full_like(theta, r) for r in near]
    rings.extend(config.refinement_radius + f * (outer - config.refinement_radius) for f in fractions)
    return np.asarray(rings)


def build_mesh(config: ModelConfig) -> Mesh:
    ntheta = config.angular_divisions
    if ntheta < 24 or ntheta % 4:
        raise ValueError("angular_divisions must be a multiple of four and at least 24")
    theta = 2.0 * np.pi * np.arange(ntheta) / ntheta
    radii = _radial_coordinates(config, theta)
    points = np.vstack([np.column_stack((r * np.cos(theta), r * np.sin(theta))) for r in radii])
    nrings = len(radii)
    triangles: list[list[int]] = []
    for ring in range(nrings - 1):
        for j in range(ntheta):
            jp = (j + 1) % ntheta
            a, b = ring * ntheta + j, ring * ntheta + jp
            c, d = (ring + 1) * ntheta + j, (ring + 1) * ntheta + jp
            triangles.extend([[a, c, d], [a, d, b]] if (ring + j) % 2 == 0 else [[a, c, b], [b, c, d]])
    tri = np.asarray(triangles, dtype=int)
    xy = points[tri]
    signed = np.cross(xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0])
    tri[signed < 0, 1], tri[signed < 0, 2] = tri[signed < 0, 2].copy(), tri[signed < 0, 1].copy()
    centroids = points[tri].mean(axis=1)

    nodes = points[tri].reshape(-1, 2).copy()
    element_nodes = np.arange(len(nodes), dtype=int).reshape(-1, 3)
    edge_map: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for e, t in enumerate(tri):
        for li, lj in ((0, 1), (1, 2), (2, 0)):
            edge_map.setdefault(tuple(sorted((int(t[li]), int(t[lj])))), []).append((e, li, lj))

    def local_face(owner: tuple[int, int, int], g0: int, g1: int) -> list[int]:
        e, li, lj = owner
        lookup = {int(tri[e, li]): int(element_nodes[e, li]), int(tri[e, lj]): int(element_nodes[e, lj])}
        return [lookup[g0], lookup[g1]]

    fa, fb, ixy, normals, lengths, oa, ob = [], [], [], [], [], [], []
    bfaces, blengths, bnormals, bkinds = [], [], [], []
    for (g0, g1), owners in edge_map.items():
        edge = points[g1] - points[g0]
        length = float(np.linalg.norm(edge))
        tangent = edge / length
        normal = np.array([-tangent[1], tangent[0]])
        midpoint = 0.5 * (points[g0] + points[g1])
        if len(owners) == 2:
            a_owner, b_owner = owners
            if np.dot(normal, centroids[b_owner[0]] - centroids[a_owner[0]]) < 0:
                normal *= -1.0
            fa.append(local_face(a_owner, g0, g1)); fb.append(local_face(b_owner, g0, g1))
            ixy.append(points[[g0, g1]]); normals.append(normal); lengths.append(length)
            oa.append(a_owner[0]); ob.append(b_owner[0])
        else:
            owner = owners[0]
            radius = np.linalg.norm(midpoint)
            inner = radius < 1.5 * config.borehole_radius
            desired = -midpoint if inner else midpoint
            if np.dot(normal, desired) < 0:
                normal *= -1.0
            bfaces.append(local_face(owner, g0, g1)); blengths.append(length); bnormals.append(normal)
            bkinds.append(0 if inner else 1)

    target = np.array([0.35 / np.sqrt(2.0), 0.35 / np.sqrt(2.0)])
    monitor = int(np.argmin(np.linalg.norm(centroids - target, axis=1)))
    return Mesh(
        points, tri, nodes, element_nodes, centroids,
        np.asarray(fa), np.asarray(fb), np.asarray(ixy), np.asarray(normals), np.asarray(lengths),
        np.asarray(oa), np.asarray(ob), np.asarray(bfaces), np.asarray(blengths), np.asarray(bnormals),
        np.asarray(bkinds), np.arange(ntheta), np.arange((nrings - 1) * ntheta, nrings * ntheta), monitor,
    )


def precompute_elements(mesh: Mesh, config: ModelConfig) -> Elements:
    xy = mesh.nodes[mesh.element_nodes]
    x1, y1 = xy[:, 0, 0], xy[:, 0, 1]
    x2, y2 = xy[:, 1, 0], xy[:, 1, 1]
    x3, y3 = xy[:, 2, 0], xy[:, 2, 1]
    twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    area = 0.5 * twice_area
    B = np.zeros((len(area), 3, 6))
    b = np.column_stack((y2 - y3, y3 - y1, y1 - y2)) / twice_area[:, None]
    c = np.column_stack((x3 - x2, x1 - x3, x2 - x1)) / twice_area[:, None]
    B[:, 0, 0::2] = b; B[:, 1, 1::2] = c; B[:, 2, 0::2] = c; B[:, 2, 1::2] = b
    jac = np.stack((xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]), axis=2)
    inv_jac = np.linalg.inv(jac)
    edges = np.stack((np.linalg.norm(xy[:, 1] - xy[:, 0], axis=1), np.linalg.norm(xy[:, 2] - xy[:, 1], axis=1), np.linalg.norm(xy[:, 0] - xy[:, 2], axis=1)), axis=1)
    nodal_mass = np.repeat(config.density * config.thickness * area / 3.0, 3)
    return Elements(B, plane_strain_matrix(config.young_modulus, config.poisson_ratio), area, nodal_mass, edges.min(axis=1), inv_jac)


def build_thermal_system(mesh: Mesh, config: ModelConfig) -> ThermalSystem:
    n = len(mesh.geometric_nodes)
    rows, cols, values = [], [], []
    capacity = np.zeros(n)
    for e, ids in enumerate(mesh.triangles):
        xy = mesh.geometric_nodes[ids]
        area = 0.5 * abs(np.cross(xy[1] - xy[0], xy[2] - xy[0]))
        b = np.array([xy[1, 1] - xy[2, 1], xy[2, 1] - xy[0, 1], xy[0, 1] - xy[1, 1]]) / (2 * area)
        c = np.array([xy[2, 0] - xy[1, 0], xy[0, 0] - xy[2, 0], xy[1, 0] - xy[0, 0]]) / (2 * area)
        ke = config.thermal_conductivity * config.thickness * area * (np.outer(b, b) + np.outer(c, c))
        capacity[ids] += config.density * config.specific_heat_capacity * config.thickness * area / 3.0
        for i in range(3):
            for j in range(3):
                rows.append(ids[i]); cols.append(ids[j]); values.append(ke[i, j])
    return ThermalSystem(capacity, coo_matrix((values, (rows, cols)), shape=(n, n)).tocsr())


def solve_temperature_history(mesh: Mesh, thermal: ThermalSystem, config: ModelConfig) -> list[np.ndarray]:
    dt = config.thermal_duration_seconds / config.thermal_stages
    matrix = thermal.conductivity + diags(thermal.capacity / dt)
    fixed = np.unique(np.r_[mesh.inner_geometric_nodes, mesh.outer_geometric_nodes])
    fixed_values = np.where(np.isin(fixed, mesh.inner_geometric_nodes), config.wall_temperature, config.initial_temperature)
    free = np.setdiff1d(np.arange(len(mesh.geometric_nodes)), fixed)
    mff, mfb = matrix[free][:, free], matrix[free][:, fixed]
    temperature = np.full(len(mesh.geometric_nodes), config.initial_temperature)
    solutions = [temperature.copy()]
    for _ in range(config.thermal_stages):
        rhs = thermal.capacity * temperature / dt
        temperature[fixed] = fixed_values
        temperature[free] = spsolve(mff, rhs[free] - mfb @ fixed_values)
        solutions.append(temperature.copy())
    return solutions


def initialize_interfaces(mesh: Mesh, config: ModelConfig) -> InterfaceState:
    midpoint = mesh.interface_xy.mean(axis=1)
    radius = np.linalg.norm(midpoint, axis=1)
    angle = np.arctan2(midpoint[:, 1], midpoint[:, 0])
    rng = np.random.default_rng(config.random_seed)
    field = np.zeros_like(radius)
    for wave in range(1, 8):
        field += rng.normal() / wave**1.25 * np.cos(wave * angle + rng.uniform(0, 2 * np.pi))
    field += 0.45 * np.sin(15.0 * radius / config.refinement_radius + rng.uniform(0, 2 * np.pi))
    field *= np.exp(-np.maximum(radius - config.borehole_radius, 0.0) / 0.65)
    field = (field - field.mean()) / max(field.std(), 1e-12)
    multiplier = np.clip(np.exp(config.strength_cov * field - 0.5 * config.strength_cov**2), 0.8, 1.2)[:, None]
    shape = (len(mesh.face_a), 2)
    return InterfaceState(
        np.zeros(shape), np.zeros(shape), np.zeros(shape),
        np.broadcast_to(config.interface_strength_scale * config.tensile_strength * multiplier, shape).copy(),
        np.broadcast_to(config.interface_strength_scale * config.cohesion * multiplier, shape).copy(),
        np.zeros(shape), np.zeros(shape, dtype=bool), np.zeros(shape),
    )


def bulk_response(mesh: Mesh, elements: Elements, config: ModelConfig, displacement: np.ndarray, temperature: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    reference = mesh.nodes[mesh.element_nodes]
    current = reference + displacement[mesh.element_nodes]
    jac = np.stack((current[:, 1] - current[:, 0], current[:, 2] - current[:, 0]), axis=2)
    F = np.einsum("eij,ejk->eik", jac, elements.inverse_reference_jacobian)
    angle = np.arctan2(F[:, 1, 0] - F[:, 0, 1], F[:, 0, 0] + F[:, 1, 1])
    co, si = np.cos(angle), np.sin(angle)
    R = np.empty_like(F); R[:, 0, 0] = co; R[:, 0, 1] = -si; R[:, 1, 0] = si; R[:, 1, 1] = co
    ref_c = reference - reference.mean(axis=1, keepdims=True)
    cur_c = current - current.mean(axis=1, keepdims=True)
    local = np.einsum("eni,eij->enj", cur_c, R)
    uel = (local - ref_c).reshape(-1, 6)
    strain = np.einsum("eij,ej->ei", elements.B, uel)
    dT = temperature[mesh.triangles].mean(axis=1) - config.initial_temperature
    eth = (1.0 + config.poisson_ratio) * config.effective_thermal_expansion * dT
    mechanical = strain.copy(); mechanical[:, 0] -= eth; mechanical[:, 1] -= eth
    stress_local = mechanical @ elements.D.T
    local_force = (-config.thickness * elements.area[:, None] * np.einsum("eji,ej->ei", elements.B, stress_local)).reshape(-1, 3, 2)
    global_force = np.einsum("enj,eij->eni", local_force, R)
    force = np.zeros_like(displacement); np.add.at(force, mesh.element_nodes.ravel(), global_force.reshape(-1, 2))
    tensor = np.zeros((len(stress_local), 2, 2)); tensor[:, 0, 0] = stress_local[:, 0]; tensor[:, 1, 1] = stress_local[:, 1]; tensor[:, 0, 1] = tensor[:, 1, 0] = stress_local[:, 2]
    tensor = np.einsum("eij,ejk,elk->eil", R, tensor, R)
    stress = np.column_stack((tensor[:, 0, 0], tensor[:, 1, 1], tensor[:, 0, 1]))
    energy = 0.5 * config.thickness * float(np.sum(elements.area * np.einsum("ei,ei->e", mechanical, stress_local)))
    return force, stress, energy


def _softening(d: np.ndarray) -> np.ndarray:
    a, b, c = 0.63, 1.8, 6.0
    first = 1.0 - ((a + b - 1.0) / (a + b)) * np.exp(d * (a + c * b) / ((a + b) * (1.0 - a - b)))
    return np.clip(first * (a * (1.0 - d) + b * (1.0 - d) ** c), 0.0, 1.0)


def cohesive_response(mesh: Mesh, config: ModelConfig, state: InterfaceState, displacement: np.ndarray, stress: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray], float, float]:
    xi = np.array([-1 / np.sqrt(3), 1 / np.sqrt(3)])
    N = np.column_stack((0.5 * (1 - xi), 0.5 * (1 + xi)))
    xa = mesh.nodes[mesh.face_a] + displacement[mesh.face_a]
    xb = mesh.nodes[mesh.face_b] + displacement[mesh.face_b]
    mid = 0.5 * (xa + xb); edge = mid[:, 1] - mid[:, 0]
    tangent = edge / np.maximum(np.linalg.norm(edge, axis=1)[:, None], 1e-30)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    reverse = np.einsum("ij,ij->i", normal, mesh.normal) < 0; normal[reverse] *= -1; tangent[reverse] *= -1
    jump = np.einsum("gi,eic->egc", N, displacement[mesh.face_b]) - np.einsum("gi,eic->egc", N, displacement[mesh.face_a])
    opening = np.einsum("egc,ec->eg", jump, normal); slip = np.einsum("egc,ec->eg", jump, tangent)
    old_damage = state.damage.copy()
    state.maximum_opening = np.maximum(state.maximum_opening, np.maximum(opening, 0)); state.maximum_slip = np.maximum(state.maximum_slip, np.abs(slip))
    length = mesh.interface_length[:, None]; penalty = config.fracture_penalty_factor * config.young_modulus
    peak_o = 2 * length * state.tensile_strength / penalty; peak_s = 2 * length * state.cohesion / penalty
    residual_o = peak_o + 3 * config.mode_i_fracture_energy / state.tensile_strength
    residual_s = peak_s + 3 * config.mode_ii_fracture_energy / state.cohesion
    di = np.maximum((state.maximum_opening - peak_o) / (residual_o - peak_o), 0)
    dii = np.maximum((state.maximum_slip - peak_s) / (residual_s - peak_s), 0)
    trial = np.clip(np.sqrt(di**2 + dii**2), 0, 1)
    mean = 0.5 * (stress[mesh.owner_a] + stress[mesh.owner_b])
    tensor = np.zeros((len(mean), 2, 2)); tensor[:, 0, 0] = mean[:, 0]; tensor[:, 1, 1] = mean[:, 1]; tensor[:, 0, 1] = tensor[:, 1, 0] = mean[:, 2]
    traction_bulk = np.einsum("eij,ej->ei", tensor, normal)
    bn = np.einsum("ei,ei->e", traction_bulk, normal)[:, None]
    bs = np.abs(np.einsum("ei,ei->e", traction_bulk, tangent))[:, None]
    state.activated |= (np.maximum(bn, 0) / state.tensile_strength >= 1) | (bs / (state.cohesion + np.maximum(-bn, 0) * config.friction_coefficient) >= 1)
    state.damage = np.maximum(state.damage, np.where(state.activated, trial, 0))
    denom = di**2 + dii**2; state.mode_mixity = np.divide(dii**2, denom, out=np.zeros_like(denom), where=denom > 0)
    soft = _softening(state.damage); stiffness = penalty / length
    ro = state.maximum_opening / peak_o; os = np.where(ro <= 1, 2 * ro - ro**2, 1)
    envelope_o = soft * state.tensile_strength * np.maximum(os, 0)
    sec_o = np.divide(envelope_o, state.maximum_opening, out=stiffness * soft, where=state.maximum_opening > 1e-16)
    tn = np.where(opening < 0, stiffness * opening, sec_o * np.maximum(opening, 0)); tn = np.where((opening >= 0) & (~state.activated), stiffness * opening, tn); tn = np.where(state.damage >= 1, np.minimum(tn, 0), tn)
    compression = np.maximum(-tn, 0); shear_strength = state.cohesion + compression * config.friction_coefficient
    rs = state.maximum_slip / peak_s; ss = np.where(rs <= 1, 2 * rs - rs**2, 1)
    envelope_s = soft * shear_strength * np.maximum(ss, 0)
    sec_s = np.divide(envelope_s, state.maximum_slip, out=stiffness * soft, where=state.maximum_slip > 1e-16)
    ts = np.where(~state.activated, stiffness * slip, sec_s * slip)
    ts = np.where(state.damage >= 1, np.clip(stiffness * slip, -compression * config.friction_coefficient, compression * config.friction_coefficient), ts)
    traction = tn[..., None] * normal[:, None, :] + ts[..., None] * tangent[:, None, :]
    jac = 0.5 * mesh.interface_length * config.thickness
    force_a = np.einsum("gi,egc,e->eic", N, traction, jac)
    force = np.zeros_like(displacement); np.add.at(force, mesh.face_a.ravel(), force_a.reshape(-1, 2)); np.add.at(force, mesh.face_b.ravel(), -force_a.reshape(-1, 2))
    cohesive_energy = float(np.sum(0.5 * (tn * np.maximum(opening, 0) + ts * slip) * jac[:, None]))
    increment = state.damage - old_damage
    mixed_G = (1 - state.mode_mixity) * config.mode_i_fracture_energy + state.mode_mixity * config.mode_ii_fracture_energy
    state.fracture_dissipation += increment * mixed_G * jac[:, None]
    return force, {"opening": opening, "slip": slip}, cohesive_energy, float(state.fracture_dissipation.sum())


def boundary_tractions(mesh: Mesh, config: ModelConfig) -> np.ndarray:
    force = np.zeros_like(mesh.nodes)
    outer = mesh.boundary_kind == 1
    traction = np.zeros_like(mesh.boundary_normal)
    far = -np.diag([config.maximum_horizontal_stress, config.minimum_horizontal_stress])
    traction[outer] = mesh.boundary_normal[outer] @ far.T
    traction[~outer] = -config.mud_pressure * mesh.boundary_normal[~outer]
    nodal = 0.5 * mesh.boundary_length[:, None] * config.thickness * traction
    np.add.at(force, mesh.boundary_face_nodes[:, 0], nodal); np.add.at(force, mesh.boundary_face_nodes[:, 1], nodal)
    return force


def _assemble_intact_stiffness(mesh: Mesh, elements: Elements, config: ModelConfig) -> csr_matrix:
    ndof = 2 * len(mesh.nodes); rows, cols, vals = [], [], []
    for e, ids in enumerate(mesh.element_nodes):
        dofs = np.ravel(np.column_stack((2 * ids, 2 * ids + 1)))
        ke = config.thickness * elements.area[e] * elements.B[e].T @ elements.D @ elements.B[e]
        rr, cc = np.meshgrid(dofs, dofs, indexing="ij"); rows.extend(rr.ravel()); cols.extend(cc.ravel()); vals.extend(ke.ravel())
    xi = np.array([-1 / np.sqrt(3), 1 / np.sqrt(3)]); N = np.column_stack((0.5 * (1 - xi), 0.5 * (1 + xi)))
    for e, (a, b) in enumerate(zip(mesh.face_a, mesh.face_b)):
        scalar = np.zeros((4, 4)); coeff_sign = np.array([-1, -1, 1, 1])
        for ng in N:
            coeff = coeff_sign * np.r_[ng, ng]
            scalar += config.fracture_penalty_factor * config.young_modulus / mesh.interface_length[e] * 0.5 * mesh.interface_length[e] * config.thickness * np.outer(coeff, coeff)
        ids = np.r_[a, b]
        for component in (0, 1):
            dofs = 2 * ids + component; rr, cc = np.meshgrid(dofs, dofs, indexing="ij")
            rows.extend(rr.ravel()); cols.extend(cc.ravel()); vals.extend(scalar.ravel())
    return coo_matrix((vals, (rows, cols)), shape=(ndof, ndof)).tocsr()


def solve_intact_prestress(mesh: Mesh, elements: Elements, config: ModelConfig) -> np.ndarray:
    K = _assemble_intact_stiffness(mesh, elements, config)
    f = boundary_tractions(mesh, config).ravel()
    ndof = len(f); G = np.zeros((3, ndof)); weights = elements.nodal_mass / elements.nodal_mass.sum()
    G[0, 0::2] = weights; G[1, 1::2] = weights
    G[2, 0::2] = -weights * mesh.nodes[:, 1]; G[2, 1::2] = weights * mesh.nodes[:, 0]
    scales = np.linalg.norm(G, axis=1); G /= scales[:, None]
    saddle = bmat([[K, csr_matrix(G.T)], [csr_matrix(G), csr_matrix((3, 3))]], format="csr")
    solution = spsolve(saddle, np.r_[f, np.zeros(3)])[:ndof]
    return solution.reshape(-1, 2)


def stable_time_step(mesh: Mesh, elements: Elements, config: ModelConfig) -> float:
    mass = elements.nodal_mass * config.dynamic_mass_scale
    interface_limit = np.sqrt(mass.min() / (config.fracture_penalty_factor * config.young_modulus * config.thickness))
    cp = np.sqrt(config.young_modulus * (1 - config.poisson_ratio) / (config.density * (1 + config.poisson_ratio) * (1 - 2 * config.poisson_ratio))) / np.sqrt(config.dynamic_mass_scale)
    wave_limit = elements.characteristic_length.min() / cp
    return config.cfl_safety * min(interface_limit, wave_limit)


def _principal_magnitude(stress: np.ndarray) -> np.ndarray:
    tensor = np.zeros((len(stress), 2, 2)); tensor[:, 0, 0] = stress[:, 0]; tensor[:, 1, 1] = stress[:, 1]; tensor[:, 0, 1] = tensor[:, 1, 0] = stress[:, 2]
    return np.max(np.abs(np.linalg.eigvalsh(tensor)), axis=1)


def run_thermal_breakout(config: ModelConfig | None = None, verbose: bool = True) -> SimulationResult:
    config = config or ModelConfig(); mesh = build_mesh(config); elements = precompute_elements(mesh, config)
    thermal = build_thermal_system(mesh, config); temperatures = solve_temperature_history(mesh, thermal, config)
    interfaces = initialize_interfaces(mesh, config)
    displacement = solve_intact_prestress(mesh, elements, config); velocity = np.zeros_like(displacement)
    outer_nodes = np.unique(mesh.boundary_face_nodes[mesh.boundary_kind == 1].ravel()); fixed_outer = displacement[outer_nodes].copy()
    mass = (elements.nodal_mass * config.dynamic_mass_scale)[:, None]
    dt = stable_time_step(mesh, elements, config)
    cp = np.sqrt(config.young_modulus * (1 - config.poisson_ratio) / (config.density * (1 + config.poisson_ratio) * (1 - 2 * config.poisson_ratio))) / np.sqrt(config.dynamic_mass_scale)
    damping = 2 * config.damping_ratio * cp / config.damping_length_scale
    total_steps = config.prestress_relax_steps + config.thermal_stages * config.steps_per_thermal_stage
    records, snapshots, stored = [], [], set(); stress = np.zeros((len(mesh.triangles), 3)); damping_work = 0.0
    for step in range(total_steps + 1):
        displacement[outer_nodes] = fixed_outer; velocity[outer_nodes] = 0
        if step < config.prestress_relax_steps:
            stage, phase = 0, "preload"
        else:
            stage = min(1 + (step - config.prestress_relax_steps) // config.steps_per_thermal_stage, config.thermal_stages); phase = "heating"
        fraction = stage / config.thermal_stages; temperature = temperatures[stage]
        fbulk, stress, bulk_energy = bulk_response(mesh, elements, config, displacement, temperature)
        fcoh, diag, cohesive_energy, fracture_energy = cohesive_response(mesh, config, interfaces, displacement, stress)
        fext = boundary_tractions(mesh, config); fdamp = -damping * mass * velocity
        total_force = fbulk + fcoh + fext + fdamp
        kinetic = 0.5 * float(np.sum(mass * velocity**2)); damping_work += float(np.sum(damping * mass * velocity**2)) * dt
        stage_end = step == config.prestress_relax_steps - 1 or (step >= config.prestress_relax_steps and (step - config.prestress_relax_steps + 1) % config.steps_per_thermal_stage == 0) or step == total_steps
        if step % config.output_interval == 0 or stage_end:
            pmag = _principal_magnitude(stress)
            records.append({
                "step": step, "mechanical_time_ms": 1e3 * step * dt, "phase": phase,
                "heating_fraction": fraction, "thermal_time_seconds": fraction * config.thermal_duration_seconds,
                "maximum_temperature_c": float(temperature.max()), "monitor_stress_magnitude_mpa": pmag[mesh.monitor_element] / 1e6,
                "maximum_principal_stress_magnitude_mpa": pmag.max() / 1e6, "maximum_damage": float(interfaces.damage.max(initial=0)),
                "yielded_interfaces": int(np.count_nonzero(interfaces.damage.max(axis=1) > 0)), "broken_interfaces": int(np.count_nonzero(interfaces.damage.max(axis=1) >= 0.999)),
                "maximum_opening_um": 1e6 * float(np.maximum(diag["opening"], 0).max(initial=0)), "maximum_slip_um": 1e6 * float(np.abs(diag["slip"]).max(initial=0)),
                "kinetic_energy_j": kinetic, "bulk_strain_energy_j": bulk_energy, "cohesive_stored_energy_j": cohesive_energy,
                "fracture_dissipation_j": fracture_energy, "damping_dissipation_j": damping_work,
                "kinetic_to_internal_ratio": kinetic / max(bulk_energy + cohesive_energy, 1e-30),
            })
        if stage_end and stage not in stored:
            if stage in {0, 3, 6, 9, config.thermal_stages}:
                label = "prestressed" if stage == 0 else f"{100 * fraction:.0f}% thermal time"
                snapshots.append(Snapshot(step, label, fraction, fraction * config.thermal_duration_seconds, temperature.copy(), displacement.copy(), stress.copy(), interfaces.damage.max(axis=1).copy(), interfaces.mode_mixity.mean(axis=1).copy()))
            stored.add(stage)
        acceleration = total_force / mass; acceleration[outer_nodes] = 0
        velocity += acceleration * dt; displacement += velocity * dt
    history = pd.DataFrame(records)
    result = SimulationResult(config, mesh, elements, history, snapshots, temperatures, displacement, velocity, stress, interfaces.damage.max(axis=1), interfaces.mode_mixity.mean(axis=1), dt, total_steps, "completed prescribed thermal stages")
    if verbose:
        final = history.iloc[-1]
        print(f"{len(mesh.triangles)} triangles, {len(mesh.face_a)} cohesive interfaces, dt={dt:.3e} s, {total_steps:,} mechanical steps")
        print(f"Final temperature = {final.maximum_temperature_c:.2f} °C; broken interfaces = {int(final.broken_interfaces)}")
    return result


def save_result_data(result: SimulationResult, directory: str | Path) -> Path:
    output = Path(directory); output.mkdir(parents=True, exist_ok=True)
    result.history.to_csv(output / "history.csv", index=False); final = result.history.iloc[-1]
    pd.Series({"triangles": len(result.mesh.triangles), "cohesive_interfaces": len(result.mesh.face_a), "time_step_seconds": result.time_step, "steps_completed": result.steps_completed, "final_maximum_temperature_c": final.maximum_temperature_c, "final_monitor_stress_magnitude_mpa": final.monitor_stress_magnitude_mpa, "yielded_interfaces_final": final.yielded_interfaces, "broken_interfaces_final": final.broken_interfaces, "termination_reason": result.termination_reason}, name="value").to_csv(output / "summary.csv", header=True)
    pd.Series(result.config.to_dict(), name="value").to_csv(output / "configuration.csv", header=True)
    return output
