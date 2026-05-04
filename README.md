# Computational Rock Mechanics Portfolio

This repository documents my ongoing numerical modelling work in rock mechanics and computational geomechanics. It is being developed as a technical portfolio while I build deeper experience in brittle rock failure, excavation response, discontinuity-controlled behaviour, slope failure, fracture processes, and numerical post-processing.

## Current focus

The portfolio currently contains three completed project case studies:

- **01. UCS brittle failure simulation**
- **02. Direct shear test simulation**
- **03. Excavation of a circular tunnel**

It will continue to expand with additional case studies such as:

- rock slope failure
- fracture network analysis
- result visualization and post-processing workflows

## Purpose

The goal of this repository is to present structured case studies that demonstrate:

- numerical modelling workflow
- interpretation of rock failure processes
- interpretation of discontinuity-controlled mechanical behaviour
- engineering understanding of stress, deformation, and fracture response
- post-processing of simulation outputs using engineering plots, images, and summaries

## Current projects

### 01. UCS brittle failure simulation

A 2D numerical simulation of unconfined compressive strength failure in a brittle rock specimen using Geomechanica Irazu. This project includes:

- fracture-pattern interpretation
- stress magnitude visualization and time-history plotting
- top platen force visualization and force-history plotting
- stress-strain post-processing and UCS estimation
- brittle failure process interpretation
- additional ParaView-based stress visualization, Plot Over Line analysis, and principal stress trajectory interpretation

Project folder:

`01_ucs_brittle_failure/`

### 02. Direct shear test simulation

A 2D numerical simulation of direct shear along a rough rock discontinuity using Geomechanica Irazu. This project includes:

- shear load versus shear displacement analysis
- shear load versus time-step response
- equivalent shear load interpretation
- instantaneous friction-angle evolution
- comparison of two normal-load cases
- minimum principal stress interpretation at selected simulation times
- Python-based post-processing of direct shear history outputs

Project folder:

`02_direct_shear_test/`

### 03. Excavation of a circular tunnel

A 2D circular tunnel excavation study in brittle geomaterial using Geomechanica Irazu. This project compares a stronger material case and a reduced-strength case under the same geometry, boundary conditions, in-situ stress state, and excavation logic. The project includes:

- comparative geometry, model setup, and material-property tables
- displacement-field evolution at selected output steps
- comparison of non-fracturing and fracturing excavation responses
- average displacement magnitude comparison for selected tunnel-region nodes
- radial and tangential displacement comparison
- average force and velocity magnitude comparison
- Python-based post-processing of exported node-history data

Project folder:

`03_tunnel_excavation_circular_opening/`

## Notes

Each project folder contains its own README, figures, processed data, notes, report materials, and scripts where applicable.

More projects will be added as the portfolio develops.
