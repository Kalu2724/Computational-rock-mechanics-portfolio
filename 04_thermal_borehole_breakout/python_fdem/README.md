# Python FDEM reconstruction of thermally induced borehole breakout

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Kalu2724/Computational-rock-mechanics-portfolio/blob/main/04_thermal_borehole_breakout/python_fdem/notebooks/Thermal_Borehole_FDEM_Reconstruction.ipynb)

I built this model to revisit my Irazu thermal-borehole assignment with a solver whose equations and update sequence I can inspect directly. It is a two-dimensional plane-strain FDEM-style reconstruction: constant-strain triangles describe intact deformation, zero-thickness cohesive interfaces soften and fail, and a finite-element heat equation supplies the temperature field.

The model uses the original 10 m × 10 m domain, 0.11 m borehole radius, 60/30 MPa horizontal stresses, 37 MPa mud pressure, 60 GPa Young's modulus, and the exported Irazu temperature and stress data for comparison.

## Governing equations

$$
\rho c_p\frac{\partial T}{\partial t}-\nabla\cdot(k\nabla T)=0,
$$

$$
\mathbf M\ddot{\mathbf u}=\mathbf f_{bulk}+\mathbf f_{coh}+\mathbf f_{boundary}-\mathbf C\dot{\mathbf u},
$$

$$
\boldsymbol\varepsilon_m=\mathbf B\mathbf u_e-(1+\nu)\alpha_{eff}\Delta T[1,1,0]^T,
\qquad \boldsymbol\sigma=\mathbf D_{plane\ strain}\boldsymbol\varepsilon_m.
$$

The shared geometric mesh solves heat conduction by backward Euler. The mechanical mesh duplicates every triangle node and reconnects neighbouring faces with two-point cohesive interfaces. A tensile/Mohr–Coulomb stress gate activates irreversible mixed-mode softening. Failed closed faces retain compression and Coulomb friction.

## Run locally

```bash
python -m pip install -r requirements.txt
python tests/test_thermomechanics.py
python run_simulation.py
```

The notebook is in `notebooks/Thermal_Borehole_FDEM_Reconstruction.ipynb`.

## Important limits

- The assignment records a thermal expansion input of $10^{-3}$/°C, but its exact Irazu definition was not retained. The reduced reconstruction keeps that value for audit and uses a separately identified effective coefficient of $1.50\times10^{-5}$/°C.
- The 6,000 s thermal duration is an effective diffusion duration calibrated against the exported radial temperature profile because the export did not preserve a defensible physical-time conversion.
- The solver resolves cohesive localization and shallow wall spalling, but it does not perform general contact search between detached fragments.
- The original stress-probe coordinates were not retained, so the stress histories are compared as normalized trends rather than as an absolute point match.
- Uniform mass scaling of 10 is checked through the reported kinetic/internal energy ratio.
