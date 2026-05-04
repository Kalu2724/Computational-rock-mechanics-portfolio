#!/usr/bin/env python
# coding: utf-8



# In[2]:


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================================================
# USER INPUTS
# =========================================================

# Use data files from the project data folder if running from the scripts folder
run1_file = "history_run_1.csv"
run2_file = "history_run_2.csv"

# Direct shear tutorial values
normal_load_run1 = 20.0   # N
normal_load_run2 = 40.0   # N
area_scaling_factor = 50.0

# =========================================================
# LOAD DATA
# =========================================================

run1 = pd.read_csv(
    run1_file,
    header=None,
    names=["time_step", "shear_displacement_mm", "shear_force_N"]
)

run2 = pd.read_csv(
    run2_file,
    header=None,
    names=["time_step", "shear_displacement_mm", "shear_force_N"]
)

# =========================================================
# DERIVED QUANTITIES
# =========================================================

run1["friction_angle_deg"] = np.degrees(
    np.arctan(run1["shear_force_N"] / normal_load_run1)
)

run2["friction_angle_deg"] = np.degrees(
    np.arctan(run2["shear_force_N"] / normal_load_run2)
)

run1["equivalent_shear_load_N"] = run1["shear_force_N"] * area_scaling_factor
run2["equivalent_shear_load_N"] = run2["shear_force_N"] * area_scaling_factor

# =========================================================
# GET PEAK INFO
# =========================================================

def get_peak_info(df):
    peak_idx = df["shear_force_N"].idxmax()
    return {
        "peak_idx": peak_idx,
        "peak_step": int(df.loc[peak_idx, "time_step"]),
        "peak_disp": df.loc[peak_idx, "shear_displacement_mm"],
        "peak_force": df.loc[peak_idx, "shear_force_N"],
        "peak_phi": df.loc[peak_idx, "friction_angle_deg"],
        "peak_equiv_force": df.loc[peak_idx, "equivalent_shear_load_N"]
    }

peak1 = get_peak_info(run1)
peak2 = get_peak_info(run2)

# =========================================================
# SUMMARY TABLE
# =========================================================

def summarize(df: pd.DataFrame, run_name: str, normal_load: float, peak_info: dict) -> dict:
    final_force = df.iloc[-1]["shear_force_N"]
    final_disp = df.iloc[-1]["shear_displacement_mm"]
    final_phi = df.iloc[-1]["friction_angle_deg"]
    final_equiv_force = df.iloc[-1]["equivalent_shear_load_N"]

    return {
        "Run": run_name,
        "Normal load (N)": normal_load,
        "Peak shear force (N)": peak_info["peak_force"],
        "Displacement at peak (mm)": peak_info["peak_disp"],
        "Time step at peak": peak_info["peak_step"],
        "Peak friction angle (deg)": peak_info["peak_phi"],
        "Peak equivalent shear load (N)": peak_info["peak_equiv_force"],
        "Final displacement (mm)": final_disp,
        "Final shear force (N)": final_force,
        "Final friction angle (deg)": final_phi,
        "Final equivalent shear load (N)": final_equiv_force
    }

summary_df = pd.DataFrame([
    summarize(run1, "Run 1", normal_load_run1, peak1),
    summarize(run2, "Run 2", normal_load_run2, peak2),
])

summary_df.to_csv("direct_shear_summary.csv", index=False)
summary_df.to_excel("direct_shear_summary.xlsx", index=False)

# =========================================================
# HELPER FUNCTION FOR PEAK ANNOTATION
# =========================================================

def annotate_peak(ax, x, y, label):
    ax.plot(x, y, marker="o", markersize=8)
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", alpha=0.3),
        arrowprops=dict(arrowstyle="->", lw=1)
    )

# =========================================================
# PLOT 1: SHEAR LOAD VS SHEAR DISPLACEMENT
# =========================================================

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(run1["shear_displacement_mm"], run1["shear_force_N"], linewidth=2, label="Run 1")
ax.plot(run2["shear_displacement_mm"], run2["shear_force_N"], linewidth=2, label="Run 2")

annotate_peak(
    ax,
    peak1["peak_disp"],
    peak1["peak_force"],
    f'Run 1 Peak\n({peak1["peak_disp"]:.3f} mm, {peak1["peak_force"]:.2f} N)'
)

annotate_peak(
    ax,
    peak2["peak_disp"],
    peak2["peak_force"],
    f'Run 2 Peak\n({peak2["peak_disp"]:.3f} mm, {peak2["peak_force"]:.2f} N)'
)

ax.set_xlabel("Shear displacement (mm)")
ax.set_ylabel("Shear load (N)")
ax.set_title("Direct Shear Test: Shear Load vs Shear Displacement")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig("direct_shear_shear_load_vs_displacement.png", dpi=300)
plt.show()

# =========================================================
# PLOT 2: FRICTION ANGLE VS SHEAR DISPLACEMENT
# =========================================================

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(run1["shear_displacement_mm"], run1["friction_angle_deg"], linewidth=2, label="Run 1")
ax.plot(run2["shear_displacement_mm"], run2["friction_angle_deg"], linewidth=2, label="Run 2")

annotate_peak(
    ax,
    peak1["peak_disp"],
    peak1["peak_phi"],
    f'Run 1 Peak\n({peak1["peak_disp"]:.3f} mm, {peak1["peak_phi"]:.2f}°)'
)

annotate_peak(
    ax,
    peak2["peak_disp"],
    peak2["peak_phi"],
    f'Run 2 Peak\n({peak2["peak_disp"]:.3f} mm, {peak2["peak_phi"]:.2f}°)'
)

ax.set_xlabel("Shear displacement (mm)")
ax.set_ylabel("Instantaneous friction angle (deg)")
ax.set_title("Direct Shear Test: Friction Angle vs Shear Displacement")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig("direct_shear_friction_angle_vs_displacement.png", dpi=300)
plt.show()

# =========================================================
# PLOT 3: EQUIVALENT SHEAR LOAD VS SHEAR DISPLACEMENT
# =========================================================

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(run1["shear_displacement_mm"], run1["equivalent_shear_load_N"], linewidth=2, label="Run 1")
ax.plot(run2["shear_displacement_mm"], run2["equivalent_shear_load_N"], linewidth=2, label="Run 2")

annotate_peak(
    ax,
    peak1["peak_disp"],
    peak1["peak_equiv_force"],
    f'Run 1 Peak\n({peak1["peak_disp"]:.3f} mm, {peak1["peak_equiv_force"]:.2f} N)'
)

annotate_peak(
    ax,
    peak2["peak_disp"],
    peak2["peak_equiv_force"],
    f'Run 2 Peak\n({peak2["peak_disp"]:.3f} mm, {peak2["peak_equiv_force"]:.2f} N)'
)

ax.set_xlabel("Shear displacement (mm)")
ax.set_ylabel("Equivalent shear load (N)")
ax.set_title("Direct Shear Test: Equivalent Shear Load vs Shear Displacement")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig("direct_shear_equivalent_shear_load_vs_displacement.png", dpi=300)
plt.show()

# =========================================================
# PLOT 4: SHEAR LOAD VS TIME STEP
# =========================================================

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(run1["time_step"], run1["shear_force_N"], linewidth=2, label="Run 1")
ax.plot(run2["time_step"], run2["shear_force_N"], linewidth=2, label="Run 2")

ax.set_xlabel("Time step")
ax.set_ylabel("Shear load (N)")
ax.set_title("Direct Shear Test: Shear Load vs Time Step")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig("direct_shear_shear_load_vs_timestep.png", dpi=300)
plt.show()

# =========================================================
# OPTIONAL EXTRA PLOT: COMBINED COMPARISON FIGURE
# =========================================================

fig, ax = plt.subplots(figsize=(10, 7))
ax.plot(run1["shear_displacement_mm"], run1["shear_force_N"], linewidth=2, label="Run 1: Shear load")
ax.plot(run2["shear_displacement_mm"], run2["shear_force_N"], linewidth=2, label="Run 2: Shear load")

annotate_peak(
    ax,
    peak1["peak_disp"],
    peak1["peak_force"],
    f'Run 1 Peak = {peak1["peak_force"]:.2f} N'
)

annotate_peak(
    ax,
    peak2["peak_disp"],
    peak2["peak_force"],
    f'Run 2 Peak = {peak2["peak_force"]:.2f} N'
)

ax.set_xlabel("Shear displacement (mm)")
ax.set_ylabel("Shear load (N)")
ax.set_title("Direct Shear Comparison: Run 1 vs Run 2")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig("direct_shear_run1_vs_run2_comparison.png", dpi=300)
plt.show()

# =========================================================
# PRINT SUMMARY
# =========================================================

print("\nSummary table:")
print(summary_df.to_string(index=False))

print("\nFiles created successfully:")
print("- direct_shear_shear_load_vs_displacement.png")
print("- direct_shear_friction_angle_vs_displacement.png")
print("- direct_shear_equivalent_shear_load_vs_displacement.png")
print("- direct_shear_shear_load_vs_timestep.png")
print("- direct_shear_run1_vs_run2_comparison.png")
print("- direct_shear_summary.csv")
print("- direct_shear_summary.xlsx")


# In[ ]:




