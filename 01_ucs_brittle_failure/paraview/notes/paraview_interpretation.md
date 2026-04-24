# ParaView Post-Processing Interpretation

## Overview

Additional post-processing was carried out in ParaView to better understand the internal stress evolution during the UCS simulation. This extended the interpretation beyond the standard Irazu result plots by examining selected tensor components, stress variation along a sampling line, and principal stress trajectory patterns using glyphs.

The tensorial variable correspondence used for the 2D stress tensor was:

- **stress 0** = σxx
- **stress 1** = σxy
- **stress 4** = σyy

The ParaView work focused on three main visualizations:
- stress-component contours
- Plot Over Line responses
- glyph representation of principal stress directions

## 1. Stress 0, corresponding to σxx

### What it represents
Stress 0 corresponds to **σxx**, the horizontal normal stress component.

### Interpretation
The σxx visualization shows how horizontal stress redistributes within the sample as axial compression progresses. Although the loading is applied vertically, internal horizontal stress develops because of elastic interaction, Poisson-type lateral response, and stress redistribution around damaged regions.

The contour field and line plot suggest that σxx does not remain uniform during loading. Instead, it evolves into a non-uniform pattern with stronger variation near the developing inclined fracture band. This indicates that brittle localization affects not only the main loading direction but also the lateral stress field inside the sample.

### Files
- `../screenshots/stress_0_sigma_xx_glyph_plot_over_line.png`
- `../animations/stress_0_sigma_xx_plot_over_line.mp4`

## 2. Stress 1, corresponding to σxy

### What it represents
Stress 1 corresponds to **σxy**, the shear stress component.

### Interpretation
The σxy results are especially important because the final UCS fracture pattern is dominated by an inclined failure band. The shear stress field becomes increasingly structured as loading progresses, and strong spatial variation develops along and around the localized rupture zone.

The Plot Over Line response shows that σxy changes substantially along the sample, which is consistent with the formation of a shear-dominated brittle failure path. The stress field does not remain symmetric or smooth near failure. Instead, it becomes highly disturbed, which supports the interpretation that localized cracking is associated with strong internal shear-stress redistribution.

### Files
- `../screenshots/stress_1_sigma_xy_glyph_plot_over_line.png`
- `../animations/stress_1_sigma_xy_plot_over_line.mp4`

## 3. Stress 4, corresponding to σyy

### What it represents
Stress 4 corresponds to **σyy**, the vertical normal stress component.

### Interpretation
The σyy field is the most directly related to the imposed UCS loading because the platens compress the specimen vertically. Early in the simulation, the vertical stress field is more dominant and broadly distributed through the sample. As brittle failure develops, this field becomes increasingly heterogeneous.

The Plot Over Line response indicates that σyy is strongly redistributed as the specimen approaches and passes peak strength. This is consistent with the idea that once the dominant fracture band forms, the sample can no longer carry axial load uniformly. Instead, stress becomes concentrated and disrupted by the evolving damage network.

### Files
- `../screenshots/stress_4_sigma_yy_glyph_plot_over_line.png`
- `../animations/stress_4_sigma_yy_plot_over_line.mp4`

## 4. Principal stress glyph interpretation

### What the glyphs show
The glyphs were used to visualize the orientation and magnitude pattern of the principal stress directions during loading.

### Interpretation
The principal stress trajectories help show how the internal stress field reorganizes as brittle failure develops. In the earlier stages, the directions are more regular. As localization progresses, the trajectories become disturbed and reoriented around the inclined damage zone.

This is important because it shows that the final fracture pattern is not random. The crack path is associated with progressive internal stress-path redistribution and evolving stress alignment around the developing rupture band.

## 5. Engineering significance

The ParaView post-processing adds a deeper interpretation to the UCS project by showing:

- how different stress tensor components evolve during loading
- how stress varies spatially along a selected line through the specimen
- how principal stress trajectories reorganize as brittle failure localizes

Together, these visualizations help connect the final fracture pattern and stress-strain behaviour to the internal mechanical processes occurring inside the specimen.

## Summary

The ParaView visualizations support the main conclusions of the UCS assignment:

- brittle failure localized into an inclined band
- internal stress redistribution became increasingly non-uniform near failure
- shear stress played an important role in the localized rupture pattern
- the axial stress field lost uniformity after peak loading
- principal stress directions were reoriented by the developing damage zone

This additional post-processing provides a more complete interpretation of the brittle failure process in the simulated UCS test.
