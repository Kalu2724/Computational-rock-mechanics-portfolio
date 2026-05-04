# Direct Shear Test Simulation in Irazu

## Overview

This project presents a 2D numerical simulation of a direct shear test on a rough rock discontinuity using Geomechanica Irazu. The study was carried out to understand the mechanical response of discontinuity asperities under constant normal load and imposed shear displacement, with particular focus on shear resistance, friction-angle evolution, equivalent shear load, and the progressive redistribution of minimum principal stress along the joint.

## Project objectives

This direct shear case study was structured around the following objectives:

1. Describe the direct shear test problem and explain the role of discontinuity asperities in the shear response.
2. Summarize the model geometry, imported CAD-based profile, mesh, and loading configuration used in the simulation.
3. Document the material and interface properties assigned to the specimen and shear box.
4. Visualize the evolution of minimum principal stress and asperity degradation for increasing simulation time.
5. Extract and plot shear load as a function of shear displacement using the `direct_shear.py` programmable-filter workflow in ParaView.
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

## Key result

The model shows that the higher-normal-load case, **Run 2**, mobilizes greater peak shear resistance than **Run 1**. Run 1 reaches a peak shear load of about **114.02 N** at **0.130 mm**, while Run 2 reaches about **160.37 N** at **0.101 mm**. The results also show strongly irregular post-peak behavior, indicating progressive asperity degradation, unstable contact loss, and residual sliding along the rough discontinuity.

## Results

### 1. Shear load versus shear displacement

The figure below shows the direct relationship between mobilized shear resistance and imposed shear displacement for both runs.

![Direct shear load vs shear displacement](figures/direct_shear_shear_load_vs_displacement.png)

#### Interpretation

Both runs develop a sharp early peak in shear resistance, followed by a pronounced post-peak drop and an irregular residual stage. This indicates that the rough discontinuity initially mobilizes strong resistance through asperity interlocking, but once local degradation and slip begin, the interface can no longer sustain the same level of shear load.

- **Run 1 peak shear load:** 114.02 N at 0.130 mm
- **Run 2 peak shear load:** 160.37 N at 0.101 mm

The higher peak shear load in Run 2 indicates that the second loading case mobilizes greater resistance along the discontinuity.

### 2. Shear load versus time step

The figure below shows the same shear-load response, now plotted against time step.

![Direct shear load vs time step](figures/direct_shear_shear_load_vs_timestep.png)

#### Interpretation

This plot confirms that the highest shear resistance is mobilized during the earlier stage of the simulation, after which both runs enter a highly fluctuating post-peak regime. The irregular response suggests repeated local asperity failure, partial re-engagement of contact points, and unstable redistribution of load along the interface.

### 3. Equivalent shear load versus shear displacement

The figure below shows the equivalent shear-load response for the actual 50 mm deep shear box using the prescribed area scaling factor of 50.

![Equivalent shear load vs shear displacement](figures/direct_shear_equivalent_shear_load_vs_displacement.png)

#### Interpretation

The equivalent shear-load response follows the same overall pattern as the direct shear-load curve.

- **Run 1 peak equivalent shear load:** 5701.13 N
- **Run 2 peak equivalent shear load:** 8018.64 N

This reinforces the conclusion that increasing the applied normal load increases the effective shear resistance of the discontinuity.

### 4. Instantaneous friction angle versus shear displacement

The figure below shows the evolution of instantaneous friction angle computed from the simulated shear load and applied normal load.

![Instantaneous friction angle vs shear displacement](figures/direct_shear_friction_angle_vs_displacement.png)

#### Interpretation

The friction-angle response shows how the apparent sliding resistance evolves during shearing.

- **Run 1 peak friction angle:** 80.05°
- **Run 2 peak friction angle:** 76.00°

Although Run 2 reaches the higher shear load, its peak friction angle is slightly lower because the normal load used in the denominator is larger. After the peak, both runs show strong oscillations in friction angle, reflecting unstable post-peak shear behavior and evolving asperity interaction.

### 5. Direct comparison of Run 1 and Run 2

The figure below provides a direct comparison of the two runs on the same plot.

![Run 1 vs Run 2 comparison](figures/direct_shear_run1_vs_run2_comparison.png)

#### Interpretation

This comparison clearly shows that:

- Run 2 mobilizes greater peak shear resistance than Run 1
- Run 2 reaches peak load slightly earlier
- both runs undergo post-peak softening and irregular residual behavior

The overall conclusion is that Run 2 is mechanically stronger in terms of peak resistance, but both runs ultimately exhibit unstable residual sliding controlled by asperity degradation and stress redistribution.

### 6. Minimum principal stress evolution: Run 1

The following images show the evolution of minimum principal stress for Run 1 at selected simulation times.

#### Run 1 at 2 million time steps
![Run 1 minimum principal stress at 2M timesteps](figures/run1_min_principal_stress_2M_timesteps.png)

#### Run 1 at 10 million time steps
![Run 1 minimum principal stress at 10M timesteps](figures/run1_min_principal_stress_10M_timesteps.png)

#### Run 1 at 20 million time steps
![Run 1 minimum principal stress at 20M timesteps](figures/run1_min_principal_stress_20M_timesteps.png)

#### Interpretation

At the early stage, the minimum principal stress field is relatively localized around a few active contact zones along the rough discontinuity. As the simulation progresses, stress redistribution becomes more pronounced near the joint, and crack development becomes more visible. By the later stage, the interface is more degraded and the stress field is transferred through fewer surviving dominant contact regions. This agrees with the reduced and unstable residual response seen in the shear-load plots.

### 7. Minimum principal stress evolution: Run 2

The following images show the evolution of minimum principal stress for Run 2 at selected simulation times.

#### Run 2 at 2 million time steps
![Run 2 minimum principal stress at 2M timesteps](figures/run2_min_principal_stress_2M_timesteps.png)

#### Run 2 at 10 million time steps
![Run 2 minimum principal stress at 10M timesteps](figures/run2_min_principal_stress_10M_timesteps.png)

#### Run 2 at 20 million time steps
![Run 2 minimum principal stress at 20M timesteps](figures/run2_min_principal_stress_20M_timesteps.png)

#### Interpretation

Run 2 shows the same broad development pattern as Run 1, but with stronger and more sustained stress concentrations along the discontinuity. Because the applied normal load is larger, the contact zones experience stronger clamping and more persistent asperity interaction. This supports the higher peak and stronger retained shear resistance seen in the Run 2 shear-load and equivalent-shear-load curves.

## Engineering significance

The direct shear results show that the rough discontinuity response is strongly controlled by asperity interaction.

The main engineering observations are:

- both runs exhibit clear pre-peak strengthening, peak resistance, and post-peak softening
- Run 2 develops higher peak shear resistance than Run 1
- friction angle evolves dynamically and becomes unstable after peak load
- stress redistribution along the joint becomes increasingly localized as shearing progresses
- later-stage behavior is governed by progressive asperity damage and unstable residual sliding

These observations are important because they show that direct shear behavior is not defined by a single constant friction value. Instead, the resistance evolves continuously with displacement, contact degradation, crack growth, and stress redistribution.

## Files in this project

- `figures/` contains the plots and selected minimum-principal-stress images
- `data/` contains processed CSV and Excel outputs
- `notes/` contains interpretation notes and draft analysis
- `report/` contains the assignment report or supporting writeup
- `scripts/` contains the Python analysis script used for post-processing

## Notes

Additional detailed interpretation is documented in:

- `notes/direct_shear_interpretation.md`

The processed summary outputs used in this project are:

- `data/direct_shear_summary.csv`
- `data/direct_shear_summary.xlsx`

This project is presented as part of my developing portfolio in numerical rock mechanics and computational geomechanics.
