# Direct Shear Test Simulation in Irazu

## Overview

This project presents a 2D numerical simulation of a direct shear test on a rough rock discontinuity using Geomechanica Irazu. The study was carried out to understand the mechanical response of discontinuity asperities under constant normal load and imposed shear displacement, with particular focus on shear resistance, friction-angle evolution, equivalent shear load, and the progressive redistribution of minimum principal stress along the joint.

## Project objectives

This direct shear case study was structured around the following objectives:

1. Describe the direct shear test problem and explain the role of discontinuity asperities in the shear response.
2. Summarize the model geometry, imported CAD-based profile, mesh, and loading configuration used in the simulation.
3. Document the material and interface properties assigned to the specimen and shear box.
4. Visualize the evolution of minimum principal stress and asperity degradation for increasing simulation time.
5. Extract and plot shear load as a function of shear displacement using the `direct_shear.py` Programmable Filter workflow in ParaView.
6. Calculate and interpret the instantaneous friction angle as a function of shear displacement.
7. Compute the equivalent shear load for the actual shear box using the prescribed area scaling factor.
8. Compare Run 1 and Run 2 and interpret the influence of normal load on shear resistance and asperity degradation.

## Model setup

### Geometry and mesh
- Imported discontinuity profile from CAD geometry
- Cross-section length: 75 mm
- Out-of-plane model depth: 1 mm
- Actual shear-box depth: 50 mm
- Shear box thickness: 5 mm
- Triangular mesh with refined resolution near the discontinuity

### Loading and boundary conditions
- Constant normal load applied to the upper shear box
- Horizontal shearing imposed through the lower shear box
- Run 1 normal load: approximately 20 N
- Run 2 normal load: approximately 40 N
- Scaling factor for equivalent real shear-box load: 50

## Results summary

The main results developed so far include:
- shear load vs shear displacement
- shear load vs time step
- instantaneous friction angle vs shear displacement
- equivalent shear load vs shear displacement
- minimum principal stress evolution images for Run 1 and Run 2
- numerical summary tables for both runs

Detailed interpretation and selected figures will be added to this project as the repository structure is completed.

## Files in this project

- `figures/` contains plots and selected result images
- `data/` contains processed CSV and Excel outputs
- `report/` contains the assignment or supporting writeup
- `notes/` contains interpretation notes and draft analysis
- `scripts/` contains post-processing scripts where applicable

## Notes

This project is presented as part of my developing portfolio in numerical rock mechanics and computational geomechanics.
