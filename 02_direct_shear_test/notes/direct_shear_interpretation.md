# Direct Shear Interpretation Notes

## Main result figures

The main result figures used in this project are:

- `direct_shear_shear_load_vs_displacement.png`
- `direct_shear_equivalent_shear_load_vs_displacement.png`
- `direct_shear_friction_angle_vs_displacement.png`
- `direct_shear_shear_load_vs_timestep.png`
- `direct_shear_run1_vs_run2_comparison.png`

The processed numerical outputs used in interpretation are:

- `direct_shear_summary.csv`
- `direct_shear_summary.xlsx`

## Shear load response

The file `direct_shear_shear_load_vs_displacement.png` shows that both runs develop a sharp early peak in shear resistance, followed by a pronounced post-peak drop and a highly irregular residual stage. This indicates that the rough discontinuity initially mobilizes strong resistance through asperity interlocking, but once local degradation and slip begin, the interface can no longer sustain the same level of shear load.

Run 1 reaches a peak shear load of about **114.02 N** at approximately **0.130 mm** displacement, whereas Run 2 reaches a higher peak shear load of about **160.37 N** at about **0.101 mm** displacement. This confirms that the higher normal load in Run 2 increases the mobilized shear resistance.

The file `direct_shear_run1_vs_run2_comparison.png` makes this contrast especially clear. Run 2 consistently develops higher peak and intermediate shear resistance than Run 1, indicating stronger normal clamping and more sustained asperity engagement.

The file `direct_shear_shear_load_vs_timestep.png` shows the same behaviour in time-step form rather than displacement form. It confirms that the strongest resistance is mobilized in the earlier portion of the simulation, followed by progressive degradation and fluctuating residual response.

## Equivalent shear load response

The file `direct_shear_equivalent_shear_load_vs_displacement.png` presents the scaled shear-load response for the actual 50 mm deep shear box using the prescribed scaling factor of 50.

Run 1 reaches a peak equivalent shear load of about **5701.13 N**, while Run 2 reaches a higher peak equivalent shear load of about **8018.64 N**. This reinforces the same conclusion obtained from the unscaled shear-load curves: increasing the applied normal load increases the effective shear resistance of the discontinuity.

This figure is particularly useful for engineering interpretation because it translates the 2D numerical result into the equivalent load level for the actual shear-box configuration.

## Instantaneous friction-angle response

The file `direct_shear_friction_angle_vs_displacement.png` shows the evolution of the instantaneous friction angle, computed from the simulated shear load divided by the applied normal load.

Run 1 reaches a peak friction angle of about **80.05°**, while Run 2 reaches a peak friction angle of about **76.00°**. Even though Run 2 achieves the higher shear load, its peak friction angle is slightly lower because the normal load used in the denominator is larger.

After the peak, both runs show strong oscillations in friction angle. This is expected, because the friction angle is calculated from the instantaneous shear load, and once the interface enters the post-peak stage, the shear load becomes highly irregular due to repeated asperity breakage, contact loss, and re-engagement. The friction-angle curve therefore reflects the unstable nature of the evolving discontinuity response.

## Minimum principal stress evolution: Run 1

The minimum principal stress evolution for Run 1 is represented by:

- `run1_min_principal_stress_2M_timesteps.png`
- `run1_min_principal_stress_5M_timesteps.png`
- `run1_min_principal_stress_10M_timesteps.png`
- `run1_min_principal_stress_15M_timesteps.png`
- `run1_min_principal_stress_20M_timesteps.png`

At early time steps, represented by `run1_min_principal_stress_2M_timesteps.png` and `run1_min_principal_stress_5M_timesteps.png`, the minimum principal stress field is still relatively localized around a few contact zones along the rough discontinuity. The interface is carrying load through isolated asperity contacts, and only limited cracking is visible near the joint.

At intermediate and later stages, represented by `run1_min_principal_stress_10M_timesteps.png`, `run1_min_principal_stress_15M_timesteps.png`, and `run1_min_principal_stress_20M_timesteps.png`, the stress redistribution becomes more pronounced near the rough joint profile. Localized tensile and compressive concentration zones develop near the most active asperities, and crack growth becomes more visible.

By the later time steps, the interface is more degraded and the stress field is transferred through fewer surviving dominant contact regions. This agrees with the fluctuating residual response observed in the shear-load plots, where Run 1 continues to carry load but at a reduced and unstable level.

## Minimum principal stress evolution: Run 2

The minimum principal stress evolution for Run 2 is represented by:

- `run2_min_principal_stress_2M_timesteps.png`
- `run2_min_principal_stress_5M_timesteps.png`
- `run2_min_principal_stress_10M_timesteps.png`
- `run2_min_principal_stress_15M_timestep.png`
- `run2_min_principal_stress_20M_timesteps.png`

Run 2 shows the same progressive development pattern, but with stronger and more sustained stress concentrations along the discontinuity. Because the applied normal load is larger, the contact zones experience stronger clamping and more persistent asperity interaction.

At early stages, shown by `run2_min_principal_stress_2M_timesteps.png` and `run2_min_principal_stress_5M_timesteps.png`, the joint already shows stronger contact response than Run 1. This suggests that the higher normal load presses the rough surfaces together more effectively and allows greater shear resistance to be mobilized before major degradation occurs.

At intermediate and later stages, shown by `run2_min_principal_stress_10M_timesteps.png`, `run2_min_principal_stress_15M_timestep.png`, and `run2_min_principal_stress_20M_timesteps.png`, local cracking and stress redistribution become increasingly visible, but the interface maintains stronger load transfer than Run 1. This supports the higher peak and stronger retained shear resistance seen in the Run 2 load-displacement and equivalent-load curves.

## Overall comparison

Taken together, the curve-based figures and the minimum-principal-stress image sequences show that increasing the normal load increases the mobilized shear resistance of the discontinuity.

Run 2 develops:
- higher peak shear load
- higher equivalent shear load
- stronger and more sustained stress concentrations along the joint
- stronger retained contact interaction in the later stages

Run 1, by contrast, loses its dominant contact structure earlier and transitions more quickly into a lower and more fluctuating residual state.

The figures therefore support the conclusion that stronger normal loading promotes more effective asperity interlocking and greater shear resistance, even though progressive degradation still develops as sliding continues.
