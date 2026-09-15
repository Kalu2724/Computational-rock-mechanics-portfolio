# Python FDEM reconstruction of the UCS model

[Open the notebook in Google Colab](https://colab.research.google.com/github/Kalu2724/Computational-rock-mechanics-portfolio/blob/main/01_ucs_brittle_failure/python_fdem/notebooks/UCS_FDEM_Reconstruction.ipynb)

This folder is my transparent Python reconstruction of the UCS case that I first
modelled in Geomechanica Irazu. The aim is not to copy a commercial solver line
for line. I wanted a codebase small enough to explain at a whiteboard, while
still retaining the pieces that make the method finite-discrete rather than a
damage-coloured finite-element model.

The implementation contains:

- an irregular Delaunay mesh of constant-strain triangles;
- a discontinuous topology with a four-node cohesive element on every internal edge;
- plane-strain elasticity with a co-rotational update after fragments begin to turn;
- Mode I, Mode II and mixed-mode softening based on the Irazu theory manual;
- an adjacent-element stress check for tensile or Mohr--Coulomb crack initiation;
- compressive closure and Coulomb friction on failed neighbouring faces;
- smooth, displacement-controlled rigid platens;
- explicit time integration, viscous dynamic relaxation and an energy audit;
- deterministic, spatially correlated interface-strength variability;
- direct comparison with the original Irazu stress-strain history.

## What the code solves

The semi-discrete equation of motion is

$$
\mathbf{M}\ddot{\mathbf{u}} + \mathbf{C}\dot{\mathbf{u}}
= \mathbf{f}_{\mathrm{bulk}} + \mathbf{f}_{\mathrm{coh}}
+ \mathbf{f}_{\mathrm{contact}}.
$$

Each triangle supplies the bulk force

$$
\mathbf{f}^{e}_{\mathrm{bulk}}
=-tA\mathbf{B}^{\mathsf T}\mathbf{D}\mathbf{B}\mathbf{u}^{e}.
$$

Two-point Gauss integration converts the normal and tangential cohesive
tractions into equal-and-opposite forces on the two faces. Damage is permanent;
unloading follows a degraded secant stiffness. A co-rotational CST calculation
removes rigid fragment rotation before strain is evaluated.

## A calibration choice I report explicitly

The cohesion and tensile strength in an FDEM input are microscopic interface
parameters. Their mapping to specimen-scale UCS depends on mesh topology,
penalty stiffness, contact treatment and the precise cohesive law. My reduced
solver therefore exposes one `interface_strength_scale` instead of pretending
that Irazu's microscopic values transfer exactly. Interface separation alone is
not allowed to start softening: the average stress in the two adjacent CST
elements must first satisfy a tensile or Mohr--Coulomb failure check. I calibrate
the one strength scalar against the 42.77 MPa reference peak, then hold it fixed
when checking mesh size, random seed and fracture energy. No individual crack
path is fitted.

## Reference comparison for the default run

| Quantity | Python FDEM | Irazu reference |
|---|---:|---:|
| Peak UCS | 44.22 MPa | 42.77 MPa |
| Peak axial strain | 0.1465% | 0.1476% |

The peak-strength difference is 3.38%, the curve RMSE over the common strain
range is 1.20 MPa, and the fitted pre-peak modulus is 30.47 GPa. The median
pre-peak kinetic/internal-energy ratio is 0.00032, which supports treating the
pre-peak loading as quasi-static. These values refer to seed 27, a 5 mm nominal
mesh, and the reported interface strength multiplier of 0.80.

## Run it

From this folder:

```bash
python -m pip install -r requirements.txt
python tests/test_mechanics.py
python run_simulation.py
```

The default simulation takes roughly one to three minutes on a laptop. The
notebook in `notebooks/` follows the same sequence and is suitable for Google
Colab.

## Files

- `fdem_ucs/model.py` — mesh, elements, cohesive law, platen loading and solver;
- `fdem_ucs/validation.py` — patch, objectivity, balance and comparison checks;
- `fdem_ucs/visualization.py` — consistent portfolio figures;
- `run_simulation.py` — command-line entry point;
- `tests/test_mechanics.py` — lightweight mechanical tests;
- `notebooks/UCS_FDEM_Reconstruction.ipynb` — the narrated, runnable study.
- `results/default_run/` — the verified history, metrics and portfolio figures.

## Scope and limitations

The model supports separation and closure of originally neighbouring element
faces. It does not yet include a global broad-phase search for contact between
arbitrary non-neighbouring fragments, element erosion, three-dimensional
effects, or Irazu's full material library. Those omissions are stated because
they matter in large-fragment post-peak motion. Peak strength and the onset of
localization are the main validation targets here; very late post-peak fragment
motion is not treated as a production-quality prediction.
