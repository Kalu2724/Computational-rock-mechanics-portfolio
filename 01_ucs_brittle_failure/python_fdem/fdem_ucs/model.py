"""Finite-discrete element model for a two-dimensional UCS test.

The implementation is deliberately inspectable. Constant-strain triangular
elements describe intact rock, coincident four-node interfaces describe
fracture, and two moving rigid platens apply the axial load through penalty
contact. It is a research and teaching implementation, not a replacement for
the complete contact and multiphysics machinery in Irazu.

All calculations use SI units. Plotting functions convert to mm, MPa and kN.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay


@dataclass(frozen=True)
class ModelConfig:
    """Geometry, material parameters and numerical controls in SI units."""

    # Geometry and loading from the Irazu UCS assignment.
    width: float = 0.050
    height: float = 0.100
    thickness: float = 0.001
    nominal_element_size: float = 0.005
    platen_width: float = 0.060
    platen_thickness: float = 0.005
    platen_velocity: float = 0.075
    loading_ramp_time: float = 2.0e-4
    platen_mode: str = "kinematic"  # "kinematic" or "contact"
    platen_friction_angle_deg: float = 6.0

    # Rock properties from the assignment.
    density: float = 2200.0
    young_modulus: float = 30.0e9
    poisson_ratio: float = 0.20
    tensile_strength: float = 2.5e6
    cohesion: float = 10.0e6
    friction_angle_deg: float = 35.0
    mode_i_fracture_energy: float = 9.4
    mode_ii_fracture_energy: float = 94.0

    # Mesh and material field.
    mesh_jitter: float = 0.16
    strength_cov: float = 0.06
    correlation_length: float = 0.012
    random_seed: int = 27
    interface_strength_scale: float = 0.80
    stress_controlled_initiation: bool = True

    # Explicit solution controls.
    fracture_penalty_factor: float = 60.0
    contact_penalty_factor: float = 30.0
    tangential_contact_ratio: float = 0.35
    damping_ratio: float = 0.25
    cfl_safety: float = 0.22
    target_axial_strain: float = 0.0020
    output_interval: int = 500
    stop_after_peak_fraction: float = 0.25
    minimum_post_peak_outputs: int = 8
    maximum_post_peak_kinetic_ratio: float = 0.35
    maximum_steps: int = 140_000

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Mesh:
    geometric_nodes: np.ndarray
    triangles: np.ndarray
    nodes: np.ndarray
    element_nodes: np.ndarray
    face_a: np.ndarray
    face_b: np.ndarray
    interface_xy: np.ndarray
    tangent: np.ndarray
    normal: np.ndarray
    interface_length: np.ndarray
    owner_a: np.ndarray
    owner_b: np.ndarray
    top_nodes: np.ndarray
    top_weights: np.ndarray
    bottom_nodes: np.ndarray
    bottom_weights: np.ndarray
    centre_element: int


@dataclass
class Elements:
    B: np.ndarray
    D: np.ndarray
    K: np.ndarray
    area: np.ndarray
    mass: np.ndarray
    characteristic_length: np.ndarray
    inverse_reference_jacobian: np.ndarray


@dataclass
class InterfaceState:
    damage: np.ndarray
    maximum_opening: np.ndarray
    maximum_slip: np.ndarray
    tensile_strength: np.ndarray
    cohesion: np.ndarray
    fracture_dissipation: np.ndarray
    mode_mixity: np.ndarray
    activated: np.ndarray


@dataclass
class Snapshot:
    step: int
    axial_strain: float
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
    final_displacement: np.ndarray
    final_velocity: np.ndarray
    final_stress: np.ndarray
    final_damage: np.ndarray
    final_mode_mixity: np.ndarray
    time_step: float
    steps_completed: int
    termination_reason: str

    @property
    def peak_ucs_mpa(self) -> float:
        return float(self.history["axial_stress_mpa"].max())

    @property
    def peak_row(self) -> pd.Series:
        return self.history.loc[self.history["axial_stress_mpa"].idxmax()]


def plane_strain_matrix(young_modulus: float, poisson_ratio: float) -> np.ndarray:
    """Return the isotropic plane-strain constitutive matrix."""
    factor = young_modulus / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    return factor * np.array(
        [
            [1.0 - poisson_ratio, poisson_ratio, 0.0],
            [poisson_ratio, 1.0 - poisson_ratio, 0.0],
            [0.0, 0.0, 0.5 * (1.0 - 2.0 * poisson_ratio)],
        ]
    )


def _counter_clockwise(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    tri = triangles.copy()
    xy = points[tri]
    signed_twice_area = np.cross(xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0])
    clockwise = signed_twice_area < 0.0
    tri[clockwise, 1], tri[clockwise, 2] = (
        tri[clockwise, 2].copy(),
        tri[clockwise, 1].copy(),
    )
    return tri


def build_mesh(config: ModelConfig) -> Mesh:
    """Create a mildly irregular triangular mesh and insert interfaces.

    Boundary points remain exactly on the rectangular specimen. Interior
    points are jittered before Delaunay triangulation to reduce directional
    bias. Every triangle receives its own nodes; adjacent faces are then tied
    by zero-thickness, four-node cohesive elements.
    """
    nx = int(round(config.width / config.nominal_element_size))
    ny = int(round(config.height / config.nominal_element_size))
    xs = np.linspace(0.0, config.width, nx + 1)
    ys = np.linspace(0.0, config.height, ny + 1)
    xx, yy = np.meshgrid(xs, ys)
    points = np.column_stack([xx.ravel(), yy.ravel()])

    rng = np.random.default_rng(config.random_seed)
    boundary = (
        np.isclose(points[:, 0], 0.0)
        | np.isclose(points[:, 0], config.width)
        | np.isclose(points[:, 1], 0.0)
        | np.isclose(points[:, 1], config.height)
    )
    jitter = config.mesh_jitter * config.nominal_element_size
    points[~boundary] += rng.uniform(-jitter, jitter, size=(np.count_nonzero(~boundary), 2))

    triangles = _counter_clockwise(points, Delaunay(points).simplices)
    centroids = points[triangles].mean(axis=1)
    order = np.lexsort((centroids[:, 0], centroids[:, 1]))
    triangles = triangles[order]
    centroids = centroids[order]

    nodes = points[triangles].reshape(-1, 2).copy()
    element_nodes = np.arange(nodes.shape[0]).reshape(-1, 3)
    edge_map: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for e, tri in enumerate(triangles):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted((int(tri[i]), int(tri[j]))))
            edge_map.setdefault(key, []).append((e, i, j))

    faces_a: list[list[int]] = []
    faces_b: list[list[int]] = []
    segments: list[np.ndarray] = []
    tangents: list[np.ndarray] = []
    normals: list[np.ndarray] = []
    lengths: list[float] = []
    owners_a: list[int] = []
    owners_b: list[int] = []
    top_node_weights: dict[int, float] = {}
    bottom_node_weights: dict[int, float] = {}

    def discontinuous_face(owner: tuple[int, int, int], g0: int, g1: int) -> list[int]:
        e, i, j = owner
        lookup = {
            int(triangles[e, i]): int(element_nodes[e, i]),
            int(triangles[e, j]): int(element_nodes[e, j]),
        }
        return [lookup[g0], lookup[g1]]

    for (g0, g1), owners in edge_map.items():
        edge = points[g1] - points[g0]
        length = float(np.linalg.norm(edge))
        if len(owners) == 1:
            face = discontinuous_face(owners[0], g0, g1)
            if np.isclose(points[g0, 1], config.height) and np.isclose(points[g1, 1], config.height):
                for node in face:
                    top_node_weights[node] = top_node_weights.get(node, 0.0) + 0.5 * length
            elif np.isclose(points[g0, 1], 0.0) and np.isclose(points[g1, 1], 0.0):
                for node in face:
                    bottom_node_weights[node] = bottom_node_weights.get(node, 0.0) + 0.5 * length
            continue
        if len(owners) != 2:
            raise RuntimeError("A two-dimensional manifold edge must have one or two owners.")

        owner_a, owner_b = owners
        face_a = discontinuous_face(owner_a, g0, g1)
        face_b = discontinuous_face(owner_b, g0, g1)
        tangent = edge / length
        normal = np.array([-tangent[1], tangent[0]])
        if np.dot(normal, centroids[owner_b[0]] - centroids[owner_a[0]]) < 0.0:
            normal *= -1.0
        faces_a.append(face_a)
        faces_b.append(face_b)
        segments.append(points[[g0, g1]])
        tangents.append(tangent)
        normals.append(normal)
        lengths.append(length)
        owners_a.append(owner_a[0])
        owners_b.append(owner_b[0])

    centre = np.array([0.5 * config.width, 0.5 * config.height])
    centre_element = int(np.argmin(np.linalg.norm(centroids - centre, axis=1)))
    top_nodes = np.array(sorted(top_node_weights), dtype=int)
    bottom_nodes = np.array(sorted(bottom_node_weights), dtype=int)

    return Mesh(
        geometric_nodes=points,
        triangles=triangles,
        nodes=nodes,
        element_nodes=element_nodes,
        face_a=np.asarray(faces_a, dtype=int),
        face_b=np.asarray(faces_b, dtype=int),
        interface_xy=np.asarray(segments),
        tangent=np.asarray(tangents),
        normal=np.asarray(normals),
        interface_length=np.asarray(lengths),
        owner_a=np.asarray(owners_a, dtype=int),
        owner_b=np.asarray(owners_b, dtype=int),
        top_nodes=top_nodes,
        top_weights=np.array([top_node_weights[n] for n in top_nodes]),
        bottom_nodes=bottom_nodes,
        bottom_weights=np.array([bottom_node_weights[n] for n in bottom_nodes]),
        centre_element=centre_element,
    )


def precompute_elements(mesh: Mesh, config: ModelConfig) -> Elements:
    """Precompute CST strain matrices, stiffness matrices and lumped masses."""
    D = plane_strain_matrix(config.young_modulus, config.poisson_ratio)
    n_elements = mesh.element_nodes.shape[0]
    B = np.zeros((n_elements, 3, 6))
    K = np.zeros((n_elements, 6, 6))
    area = np.zeros(n_elements)
    characteristic_length = np.zeros(n_elements)
    mass = np.zeros(mesh.nodes.shape[0])
    inverse_reference_jacobian = np.zeros((n_elements, 2, 2))

    for e, connectivity in enumerate(mesh.element_nodes):
        xy = mesh.nodes[connectivity]
        x1, y1 = xy[0]
        x2, y2 = xy[1]
        x3, y3 = xy[2]
        twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if twice_area <= 0.0:
            raise ValueError("The mesh contains a clockwise or degenerate triangle.")
        area[e] = 0.5 * twice_area
        b1, b2, b3 = y2 - y3, y3 - y1, y1 - y2
        c1, c2, c3 = x3 - x2, x1 - x3, x2 - x1
        B[e] = np.array(
            [
                [b1, 0.0, b2, 0.0, b3, 0.0],
                [0.0, c1, 0.0, c2, 0.0, c3],
                [c1, b1, c2, b2, c3, b3],
            ]
        ) / twice_area
        K[e] = config.thickness * area[e] * (B[e].T @ D @ B[e])
        mass[connectivity] += config.density * config.thickness * area[e] / 3.0
        edge_lengths = np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1)
        characteristic_length[e] = 2.0 * area[e] / edge_lengths.max()
        reference_jacobian = np.column_stack([xy[1] - xy[0], xy[2] - xy[0]])
        inverse_reference_jacobian[e] = np.linalg.inv(reference_jacobian)

    return Elements(
        B=B,
        D=D,
        K=K,
        area=area,
        mass=mass,
        characteristic_length=characteristic_length,
        inverse_reference_jacobian=inverse_reference_jacobian,
    )


def _correlated_strength(mesh: Mesh, config: ModelConfig) -> np.ndarray:
    """Sample a smooth, reproducible lognormal strength multiplier field."""
    h = config.nominal_element_size
    nx = int(round(config.width / h)) + 1
    ny = int(round(config.height / h)) + 1
    rng = np.random.default_rng(config.random_seed + 911)
    field = rng.normal(size=(ny, nx))
    sigma = max(config.correlation_length / h, 0.5)
    field = gaussian_filter(field, sigma=sigma, mode="reflect")
    field = (field - field.mean()) / max(field.std(), 1.0e-12)
    interpolator = RegularGridInterpolator(
        (np.linspace(0.0, config.height, ny), np.linspace(0.0, config.width, nx)),
        field,
        bounds_error=False,
        fill_value=None,
    )
    midpoints = mesh.interface_xy.mean(axis=1)
    z = interpolator(np.column_stack([midpoints[:, 1], midpoints[:, 0]]))
    multiplier = np.exp(config.strength_cov * z - 0.5 * config.strength_cov**2)
    return np.clip(multiplier, 0.82, 1.18)


def initialize_interfaces(mesh: Mesh, config: ModelConfig) -> InterfaceState:
    multiplier = _correlated_strength(mesh, config)[:, None]
    shape = (mesh.face_a.shape[0], 2)
    return InterfaceState(
        damage=np.zeros(shape),
        maximum_opening=np.zeros(shape),
        maximum_slip=np.zeros(shape),
        tensile_strength=np.broadcast_to(
            config.interface_strength_scale * config.tensile_strength * multiplier, shape
        ).copy(),
        cohesion=np.broadcast_to(
            config.interface_strength_scale * config.cohesion * multiplier, shape
        ).copy(),
        fracture_dissipation=np.zeros(shape),
        mode_mixity=np.zeros(shape),
        activated=np.zeros(shape, dtype=bool),
    )


def bulk_response(mesh: Mesh, elements: Elements, displacement: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return co-rotational CST forces, Cauchy stress and strain energy.

    Removing each triangle's rigid rotation is essential after localization;
    otherwise a small-strain element incorrectly converts fragment rotation
    into elastic strain and the post-peak solution gains spurious energy.
    """
    reference = mesh.nodes[mesh.element_nodes]
    current = reference + displacement[mesh.element_nodes]
    current_jacobian = np.stack(
        [current[:, 1] - current[:, 0], current[:, 2] - current[:, 0]], axis=2
    )
    deformation_gradient = np.einsum(
        "eij,ejk->eik", current_jacobian, elements.inverse_reference_jacobian
    )
    # Closed-form two-dimensional polar rotation.
    angle = np.arctan2(
        deformation_gradient[:, 1, 0] - deformation_gradient[:, 0, 1],
        deformation_gradient[:, 0, 0] + deformation_gradient[:, 1, 1],
    )
    cosine, sine = np.cos(angle), np.sin(angle)
    rotation = np.empty_like(deformation_gradient)
    rotation[:, 0, 0] = cosine
    rotation[:, 0, 1] = -sine
    rotation[:, 1, 0] = sine
    rotation[:, 1, 1] = cosine

    reference_centred = reference - reference.mean(axis=1, keepdims=True)
    current_centred = current - current.mean(axis=1, keepdims=True)
    current_local = np.einsum("eni,eij->enj", current_centred, rotation)
    element_u = (current_local - reference_centred).reshape(-1, 6)
    local_force = -np.einsum("eij,ej->ei", elements.K, element_u).reshape(-1, 3, 2)
    global_force = np.einsum("enj,eij->eni", local_force, rotation)
    strain = np.einsum("eij,ej->ei", elements.B, element_u)
    stress_local = strain @ elements.D.T
    stress_tensor_local = np.zeros((stress_local.shape[0], 2, 2))
    stress_tensor_local[:, 0, 0] = stress_local[:, 0]
    stress_tensor_local[:, 1, 1] = stress_local[:, 1]
    stress_tensor_local[:, 0, 1] = stress_local[:, 2]
    stress_tensor_local[:, 1, 0] = stress_local[:, 2]
    stress_tensor = np.einsum(
        "eij,ejk,elk->eil", rotation, stress_tensor_local, rotation
    )
    stress = np.column_stack(
        [stress_tensor[:, 0, 0], stress_tensor[:, 1, 1], stress_tensor[:, 0, 1]]
    )
    force = np.zeros_like(displacement)
    np.add.at(force, mesh.element_nodes.ravel(), global_force.reshape(-1, 2))
    energy = 0.5 * float(np.einsum("ei,eij,ej->", element_u, elements.K, element_u))
    return force, stress, energy


def _softening_function(damage: np.ndarray) -> np.ndarray:
    """Munjiza softening function used by the Irazu theory manual (Eq. 48)."""
    a, b, c = 0.63, 1.8, 6.0
    d = np.clip(damage, 0.0, 1.0)
    first = 1.0 - ((a + b - 1.0) / (a + b)) * np.exp(
        d * (a + c * b) / ((a + b) * (1.0 - a - b))
    )
    second = a * (1.0 - d) + b * (1.0 - d) ** c
    return np.clip(first * second, 0.0, 1.0)


def cohesive_response(
    mesh: Mesh,
    config: ModelConfig,
    state: InterfaceState,
    displacement: np.ndarray,
    element_stress: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray], float, float]:
    """Integrate four-node cohesive tractions at two Gauss points.

    The opening/slip thresholds and post-peak softening follow Eqs. 42--55
    of the Irazu theory manual. A common irreversible damage variable couples
    Mode I and Mode II. Closed faces retain compression and Coulomb friction.
    """
    xi = np.array([-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)])
    N = np.column_stack([0.5 * (1.0 - xi), 0.5 * (1.0 + xi)])
    xa = mesh.nodes[mesh.face_a] + displacement[mesh.face_a]
    xb = mesh.nodes[mesh.face_b] + displacement[mesh.face_b]
    ua = displacement[mesh.face_a]
    ub = displacement[mesh.face_b]
    midline = 0.5 * (xa + xb)
    current_edge = midline[:, 1] - midline[:, 0]
    current_length = np.linalg.norm(current_edge, axis=1)
    current_tangent = current_edge / np.maximum(current_length[:, None], 1.0e-30)
    current_normal = np.column_stack([-current_tangent[:, 1], current_tangent[:, 0]])
    reverse = np.einsum("ij,ij->i", current_normal, mesh.normal) < 0.0
    current_normal[reverse] *= -1.0
    current_tangent[reverse] *= -1.0
    ua_gp = np.einsum("gi,eic->egc", N, ua)
    ub_gp = np.einsum("gi,eic->egc", N, ub)
    jump = ub_gp - ua_gp
    opening = np.einsum("egc,ec->eg", jump, current_normal)
    slip = np.einsum("egc,ec->eg", jump, current_tangent)

    old_damage = state.damage.copy()
    state.maximum_opening = np.maximum(state.maximum_opening, np.maximum(opening, 0.0))
    state.maximum_slip = np.maximum(state.maximum_slip, np.abs(slip))

    h = mesh.interface_length[:, None]
    pf = config.fracture_penalty_factor * config.young_modulus
    peak_opening = 2.0 * h * state.tensile_strength / pf
    peak_slip = 2.0 * h * state.cohesion / pf
    residual_opening = peak_opening + 3.0 * config.mode_i_fracture_energy / state.tensile_strength
    residual_slip = peak_slip + 3.0 * config.mode_ii_fracture_energy / state.cohesion

    d_i = np.maximum((state.maximum_opening - peak_opening) / (residual_opening - peak_opening), 0.0)
    d_ii = np.maximum((state.maximum_slip - peak_slip) / (residual_slip - peak_slip), 0.0)
    damage_trial = np.clip(np.sqrt(d_i**2 + d_ii**2), 0.0, 1.0)
    if config.stress_controlled_initiation and element_stress is not None:
        mean_stress_voigt = 0.5 * (
            element_stress[mesh.owner_a] + element_stress[mesh.owner_b]
        )
        mean_stress = np.zeros((mean_stress_voigt.shape[0], 2, 2))
        mean_stress[:, 0, 0] = mean_stress_voigt[:, 0]
        mean_stress[:, 1, 1] = mean_stress_voigt[:, 1]
        mean_stress[:, 0, 1] = mean_stress_voigt[:, 2]
        mean_stress[:, 1, 0] = mean_stress_voigt[:, 2]
        traction_from_bulk = np.einsum("eij,ej->ei", mean_stress, current_normal)
        bulk_normal = np.einsum("ei,ei->e", traction_from_bulk, current_normal)[:, None]
        bulk_shear = np.abs(
            np.einsum("ei,ei->e", traction_from_bulk, current_tangent)
        )[:, None]
        tensile_index = np.maximum(bulk_normal, 0.0) / state.tensile_strength
        shear_capacity = state.cohesion + np.maximum(-bulk_normal, 0.0) * np.tan(
            np.deg2rad(config.friction_angle_deg)
        )
        shear_index = bulk_shear / shear_capacity
        state.activated |= (tensile_index >= 1.0) | (shear_index >= 1.0)
        damage_trial = np.where(state.activated, damage_trial, 0.0)
    else:
        state.activated |= damage_trial > 0.0
    state.damage = np.maximum(state.damage, damage_trial)
    denominator = d_i**2 + d_ii**2
    state.mode_mixity = np.divide(d_ii**2, denominator, out=np.zeros_like(denominator), where=denominator > 0.0)

    softening = _softening_function(state.damage)
    kn = pf / (2.0 * h)
    # Manual Eq. 52 has initial slope pf/h. The factor above is combined with
    # the 2r-r^2 pre-peak envelope below.
    # Secant unloading/reloading prevents a damaged interface from recovering
    # its original stiffness during explicit oscillations.
    maximum_opening_ratio = np.minimum(state.maximum_opening / peak_opening, 1.0e6)
    normal_peak_factor = np.where(
        maximum_opening_ratio <= 1.0,
        2.0 * maximum_opening_ratio - maximum_opening_ratio**2,
        1.0,
    )
    normal_history_envelope = softening * state.tensile_strength * np.maximum(normal_peak_factor, 0.0)
    normal_secant = np.divide(
        normal_history_envelope,
        state.maximum_opening,
        out=(pf / h) * softening,
        where=state.maximum_opening > 1.0e-16,
    )
    normal_traction = np.where(
        opening < 0.0,
        (pf / h) * opening,
        normal_secant * np.maximum(opening, 0.0),
    )
    normal_traction = np.where(
        (opening >= 0.0) & (~state.activated), (pf / h) * opening, normal_traction
    )
    normal_traction = np.where(state.damage >= 1.0, np.minimum(normal_traction, 0.0), normal_traction)

    compression = np.maximum(-normal_traction, 0.0)
    shear_strength = state.cohesion + compression * np.tan(np.deg2rad(config.friction_angle_deg))
    maximum_slip_ratio = np.minimum(state.maximum_slip / peak_slip, 1.0e6)
    shear_peak_factor = np.where(
        maximum_slip_ratio <= 1.0,
        2.0 * maximum_slip_ratio - maximum_slip_ratio**2,
        1.0,
    )
    shear_history_envelope = softening * shear_strength * np.maximum(shear_peak_factor, 0.0)
    shear_secant = np.divide(
        shear_history_envelope,
        state.maximum_slip,
        out=(pf / h) * softening,
        where=state.maximum_slip > 1.0e-16,
    )
    shear_traction = shear_secant * slip
    shear_traction = np.where(~state.activated, (pf / h) * slip, shear_traction)
    friction_cap = compression * np.tan(np.deg2rad(config.friction_angle_deg))
    shear_traction = np.where(
        state.damage >= 1.0,
        np.clip((pf / h) * slip, -friction_cap, friction_cap),
        shear_traction,
    )

    traction = (
        normal_traction[..., None] * current_normal[:, None, :]
        + shear_traction[..., None] * current_tangent[:, None, :]
    )
    jacobian = 0.5 * mesh.interface_length * config.thickness
    nodal_force_a = np.einsum("gi,egc,e->eic", N, traction, jacobian)
    force = np.zeros_like(displacement)
    np.add.at(force, mesh.face_a.ravel(), nodal_force_a.reshape(-1, 2))
    np.add.at(force, mesh.face_b.ravel(), -nodal_force_a.reshape(-1, 2))

    cohesive_energy = float(
        np.sum(0.5 * (normal_traction * np.maximum(opening, 0.0) + shear_traction * slip) * jacobian[:, None])
    )
    damage_increment = state.damage - old_damage
    mode_i_weight = 1.0 - state.mode_mixity
    mixed_energy = (
        mode_i_weight * config.mode_i_fracture_energy
        + state.mode_mixity * config.mode_ii_fracture_energy
    )
    state.fracture_dissipation += damage_increment * mixed_energy * jacobian[:, None]
    diagnostics = {
        "opening": opening,
        "slip": slip,
        "normal_traction": normal_traction,
        "shear_traction": shear_traction,
    }
    return force, diagnostics, cohesive_energy, float(state.fracture_dissipation.sum())


def platen_contact(
    mesh: Mesh,
    config: ModelConfig,
    displacement: np.ndarray,
    velocity: np.ndarray,
    platen_displacement: float,
    dt: float,
    top_slip: np.ndarray,
    bottom_slip: np.ndarray,
) -> tuple[np.ndarray, float, float, float]:
    """Apply penalty contact and regularized Coulomb friction at both platens."""
    force = np.zeros_like(displacement)
    current = mesh.nodes + displacement
    top_y = config.height - platen_displacement
    bottom_y = platen_displacement
    k_normal = config.contact_penalty_factor * config.young_modulus / config.nominal_element_size
    k_tangent = config.tangential_contact_ratio * k_normal
    friction = np.tan(np.deg2rad(config.platen_friction_angle_deg))

    top_penetration = np.maximum(current[mesh.top_nodes, 1] - top_y, 0.0)
    bottom_penetration = np.maximum(bottom_y - current[mesh.bottom_nodes, 1], 0.0)
    top_normal = k_normal * top_penetration * mesh.top_weights * config.thickness
    bottom_normal = k_normal * bottom_penetration * mesh.bottom_weights * config.thickness

    top_active = top_penetration > 0.0
    bottom_active = bottom_penetration > 0.0
    top_slip[~top_active] = 0.0
    bottom_slip[~bottom_active] = 0.0
    top_slip[top_active] += velocity[mesh.top_nodes[top_active], 0] * dt
    bottom_slip[bottom_active] += velocity[mesh.bottom_nodes[bottom_active], 0] * dt
    top_tangent_trial = -k_tangent * top_slip * mesh.top_weights * config.thickness
    bottom_tangent_trial = -k_tangent * bottom_slip * mesh.bottom_weights * config.thickness
    top_tangent = np.clip(top_tangent_trial, -friction * top_normal, friction * top_normal)
    bottom_tangent = np.clip(bottom_tangent_trial, -friction * bottom_normal, friction * bottom_normal)

    top_sliding = np.abs(top_tangent_trial) > friction * top_normal
    bottom_sliding = np.abs(bottom_tangent_trial) > friction * bottom_normal
    top_slip[top_sliding] = -top_tangent[top_sliding] / np.maximum(
        k_tangent * mesh.top_weights[top_sliding] * config.thickness, 1.0e-30
    )
    bottom_slip[bottom_sliding] = -bottom_tangent[bottom_sliding] / np.maximum(
        k_tangent * mesh.bottom_weights[bottom_sliding] * config.thickness, 1.0e-30
    )

    force[mesh.top_nodes, 1] -= top_normal
    force[mesh.bottom_nodes, 1] += bottom_normal
    force[mesh.top_nodes, 0] += top_tangent
    force[mesh.bottom_nodes, 0] += bottom_tangent
    contact_energy = 0.5 * float(
        np.sum(top_normal * top_penetration) + np.sum(bottom_normal * bottom_penetration)
    )
    return force, float(top_normal.sum()), float(bottom_normal.sum()), contact_energy


def platen_kinematics(time: float, config: ModelConfig) -> tuple[float, float]:
    """Smoothly ramp each platen to its specified constant velocity.

    The half-cosine ramp suppresses the non-physical stress wave generated by
    applying the full platen velocity in a single explicit step.
    """
    ramp = config.loading_ramp_time
    if ramp <= 0.0 or time >= ramp:
        return config.platen_velocity * (time - 0.5 * max(ramp, 0.0)), config.platen_velocity
    phase = np.pi * time / ramp
    velocity = 0.5 * config.platen_velocity * (1.0 - np.cos(phase))
    displacement = 0.5 * config.platen_velocity * (time - ramp * np.sin(phase) / np.pi)
    return displacement, velocity


def stable_time_step(mesh: Mesh, elements: Elements, config: ModelConfig) -> float:
    """Estimate a conservative step from wave and penalty stiffness limits."""
    cp = np.sqrt(
        config.young_modulus * (1.0 - config.poisson_ratio)
        / (config.density * (1.0 + config.poisson_ratio) * (1.0 - 2.0 * config.poisson_ratio))
    )
    wave_limit = float(elements.characteristic_length.min() / cp)
    pf = config.fracture_penalty_factor * config.young_modulus
    interface_stiffness = pf * config.thickness
    contact_stiffness = (
        config.contact_penalty_factor
        * config.young_modulus
        / config.nominal_element_size
        * max(mesh.top_weights.max(), mesh.bottom_weights.max())
        * config.thickness
    )
    active_penalty = max(interface_stiffness, contact_stiffness) if config.platen_mode == "contact" else interface_stiffness
    penalty_limit = float(np.sqrt(elements.mass.min() / active_penalty))
    return config.cfl_safety * min(wave_limit, penalty_limit)


def run_ucs(config: ModelConfig | None = None, verbose: bool = True) -> SimulationResult:
    """Run the explicit UCS simulation and return histories plus snapshots."""
    config = config or ModelConfig()
    mesh = build_mesh(config)
    elements = precompute_elements(mesh, config)
    interfaces = initialize_interfaces(mesh, config)
    dt = stable_time_step(mesh, elements, config)
    target_displacement = 0.5 * config.target_axial_strain * config.height
    ramp_displacement = 0.5 * config.platen_velocity * config.loading_ramp_time
    if target_displacement <= ramp_displacement:
        # Only used for very small verification runs; bisection avoids adding
        # another analytical special case for the ramp integral.
        low, high = 0.0, config.loading_ramp_time
        for _ in range(50):
            mid = 0.5 * (low + high)
            if platen_kinematics(mid, config)[0] < target_displacement:
                low = mid
            else:
                high = mid
        target_time = 0.5 * (low + high)
    else:
        target_time = config.loading_ramp_time + (
            target_displacement - ramp_displacement
        ) / config.platen_velocity
    planned_steps = min(int(np.ceil(target_time / dt)), config.maximum_steps)

    displacement = np.zeros_like(mesh.nodes)
    velocity_half = np.zeros_like(mesh.nodes)
    stress = np.zeros((mesh.element_nodes.shape[0], 3))
    top_slip = np.zeros(mesh.top_nodes.size)
    bottom_slip = np.zeros(mesh.bottom_nodes.size)
    records: list[dict[str, float]] = []
    snapshots: list[Snapshot] = []
    external_work = 0.0
    damping_work = 0.0
    peak_stress = 0.0
    peak_output_index = 0
    termination_reason = "target axial strain reached"

    cp = np.sqrt(
        config.young_modulus * (1.0 - config.poisson_ratio)
        / (config.density * (1.0 + config.poisson_ratio) * (1.0 - 2.0 * config.poisson_ratio))
    )
    damping_rate = 2.0 * config.damping_ratio * cp / config.height
    mass_column = elements.mass[:, None]

    for step in range(planned_steps + 1):
        time = step * dt
        platen_displacement, current_platen_velocity = platen_kinematics(time, config)
        if config.platen_mode == "kinematic":
            displacement[mesh.top_nodes, 1] = -platen_displacement
            displacement[mesh.bottom_nodes, 1] = platen_displacement
            velocity_half[mesh.top_nodes, 1] = -current_platen_velocity
            velocity_half[mesh.bottom_nodes, 1] = current_platen_velocity
        bulk_force, stress, bulk_energy = bulk_response(mesh, elements, displacement)
        cohesive_force, interface_diag, cohesive_energy, fracture_energy = cohesive_response(
            mesh, config, interfaces, displacement, stress
        )
        if config.platen_mode == "contact":
            contact_force, top_reaction, bottom_reaction, contact_energy = platen_contact(
                mesh,
                config,
                displacement,
                velocity_half,
                platen_displacement,
                dt,
                top_slip,
                bottom_slip,
            )
        elif config.platen_mode == "kinematic":
            contact_force = np.zeros_like(displacement)
            contact_energy = 0.0
            internal_without_platen = bulk_force + cohesive_force
            top_normal_nodal = np.abs(internal_without_platen[mesh.top_nodes, 1])
            bottom_normal_nodal = np.abs(internal_without_platen[mesh.bottom_nodes, 1])
            top_reaction = float(top_normal_nodal.sum())
            bottom_reaction = float(bottom_normal_nodal.sum())
            # The vertical platen motion is prescribed, while horizontal end
            # slip is limited by the assignment's 6-degree platen friction.
            # A penalty spring regularizes sticking before the Coulomb cap.
            tangential_stiffness = (
                config.tangential_contact_ratio
                * config.contact_penalty_factor
                * config.young_modulus
                / config.nominal_element_size
            )
            friction = np.tan(np.deg2rad(config.platen_friction_angle_deg))
            top_trial = (
                -tangential_stiffness
                * displacement[mesh.top_nodes, 0]
                * mesh.top_weights
                * config.thickness
            )
            bottom_trial = (
                -tangential_stiffness
                * displacement[mesh.bottom_nodes, 0]
                * mesh.bottom_weights
                * config.thickness
            )
            contact_force[mesh.top_nodes, 0] = np.clip(
                top_trial, -friction * top_normal_nodal, friction * top_normal_nodal
            )
            contact_force[mesh.bottom_nodes, 0] = np.clip(
                bottom_trial, -friction * bottom_normal_nodal, friction * bottom_normal_nodal
            )
        else:
            raise ValueError("platen_mode must be 'kinematic' or 'contact'.")
        damping_force = -damping_rate * mass_column * velocity_half
        total_force = bulk_force + cohesive_force + contact_force + damping_force

        mean_reaction = 0.5 * (top_reaction + bottom_reaction)
        axial_stress = mean_reaction / (config.width * config.thickness)
        axial_strain = 2.0 * platen_displacement / config.height
        kinetic_energy = 0.5 * float(np.sum(mass_column * velocity_half**2))
        damping_work += float(np.sum(damping_rate * mass_column * velocity_half**2)) * dt
        if step > 0:
            external_work += (top_reaction + bottom_reaction) * current_platen_velocity * dt

        is_output = step % config.output_interval == 0 or step == planned_steps
        if is_output:
            internal_energy = bulk_energy + cohesive_energy + contact_energy
            centre_sigma = stress[mesh.centre_element]
            maximum_damage = float(interfaces.damage.max(initial=0.0))
            records.append(
                {
                    "step": step,
                    "time_ms": 1.0e3 * time,
                    "axial_strain": axial_strain,
                    "axial_strain_percent": 100.0 * axial_strain,
                    "axial_stress_mpa": axial_stress / 1.0e6,
                    "mean_platen_force_kn": mean_reaction / 1.0e3,
                    "top_platen_force_kn": top_reaction / 1.0e3,
                    "bottom_platen_force_kn": bottom_reaction / 1.0e3,
                    "centre_sigma_xx_mpa": centre_sigma[0] / 1.0e6,
                    "centre_sigma_yy_mpa": centre_sigma[1] / 1.0e6,
                    "centre_tau_xy_mpa": centre_sigma[2] / 1.0e6,
                    "maximum_damage": maximum_damage,
                    "yielded_interfaces": np.count_nonzero(interfaces.damage.max(axis=1) > 0.0),
                    "broken_interfaces": np.count_nonzero(interfaces.damage.max(axis=1) >= 0.999),
                    "maximum_opening_um": 1.0e6 * float(np.maximum(interface_diag["opening"], 0.0).max(initial=0.0)),
                    "maximum_slip_um": 1.0e6 * float(np.abs(interface_diag["slip"]).max(initial=0.0)),
                    "kinetic_energy_j": kinetic_energy,
                    "bulk_strain_energy_j": bulk_energy,
                    "cohesive_stored_energy_j": cohesive_energy,
                    "contact_energy_j": contact_energy,
                    "fracture_dissipation_j": fracture_energy,
                    "damping_dissipation_j": damping_work,
                    "external_work_j": external_work,
                    "kinetic_to_internal_ratio": kinetic_energy / max(internal_energy, 1.0e-30),
                    "energy_residual_j": external_work
                    - (kinetic_energy + internal_energy + fracture_energy + damping_work),
                }
            )
            snapshots.append(
                Snapshot(
                    step=step,
                    axial_strain=axial_strain,
                    displacement=displacement.copy(),
                    element_stress=stress.copy(),
                    interface_damage=interfaces.damage.max(axis=1).copy(),
                    mode_mixity=interfaces.mode_mixity.mean(axis=1).copy(),
                )
            )
            if axial_stress > peak_stress:
                peak_stress = axial_stress
                peak_output_index = len(records) - 1
            outputs_after_peak = len(records) - 1 - peak_output_index
            if (
                peak_stress > 5.0e6
                and outputs_after_peak >= config.minimum_post_peak_outputs
                and axial_stress < config.stop_after_peak_fraction * peak_stress
            ):
                termination_reason = "post-peak load-loss criterion"
                break
            if (
                interfaces.damage.max(initial=0.0) >= 0.999
                and outputs_after_peak >= 4
                and kinetic_energy / max(internal_energy, 1.0e-30)
                > config.maximum_post_peak_kinetic_ratio
            ):
                termination_reason = "post-peak kinetic-energy limit"
                break

        acceleration = total_force / mass_column
        if config.platen_mode == "kinematic":
            acceleration[mesh.top_nodes, 1] = 0.0
            acceleration[mesh.bottom_nodes, 1] = 0.0
        velocity_half += acceleration * dt
        displacement += velocity_half * dt
        # Remove only the mass-weighted horizontal rigid-body mode.
        mean_vx = float(np.sum(elements.mass * velocity_half[:, 0]) / np.sum(elements.mass))
        velocity_half[:, 0] -= mean_vx

    history = pd.DataFrame.from_records(records)
    result = SimulationResult(
        config=config,
        mesh=mesh,
        elements=elements,
        history=history,
        snapshots=snapshots,
        final_displacement=displacement,
        final_velocity=velocity_half,
        final_stress=stress,
        final_damage=interfaces.damage.max(axis=1).copy(),
        final_mode_mixity=interfaces.mode_mixity.mean(axis=1).copy(),
        time_step=dt,
        steps_completed=step,
        termination_reason=termination_reason,
    )
    if verbose:
        print(
            f"{mesh.element_nodes.shape[0]} triangles, {mesh.face_a.shape[0]} interfaces, "
            f"dt={dt:.3e} s, {step:,} steps"
        )
        print(f"Peak UCS = {result.peak_ucs_mpa:.2f} MPa at {result.peak_row['axial_strain_percent']:.4f}% strain")
        print(f"Termination: {termination_reason}")
    return result


def save_result_data(result: SimulationResult, directory: str | Path) -> Path:
    """Save numerical histories and compact metadata; figures live elsewhere."""
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    result.history.to_csv(output / "history.csv", index=False)
    summary = pd.Series(
        {
            "peak_ucs_mpa": result.peak_ucs_mpa,
            "peak_strain_percent": float(result.peak_row["axial_strain_percent"]),
            "time_step_seconds": result.time_step,
            "steps_completed": result.steps_completed,
            "triangles": result.mesh.element_nodes.shape[0],
            "cohesive_interfaces": result.mesh.face_a.shape[0],
            "broken_interfaces_final": int(np.count_nonzero(result.final_damage >= 0.999)),
            "termination_reason": result.termination_reason,
        },
        name="value",
    )
    summary.to_csv(output / "summary.csv", header=True)
    pd.Series(result.config.to_dict(), name="value").to_csv(output / "configuration.csv", header=True)
    return output
