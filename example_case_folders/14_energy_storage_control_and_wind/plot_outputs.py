# Plot the outputs of the simulation

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

labels = ["aggressive", "protective"]
battery_cols = ["C2", "teal"]
linestyles = ["-", "--"]
output_files = ["outputs/hercules_output_ag.csv", "outputs/hercules_output_pr.csv"]

# Plotting colors for non-battery components
wind_col = "C0"
solar_col = "C1"
plant_col = "C3"

_, ax_tracking = plt.subplots(2, 1, sharex=True, figsize=(7,5))
_, ax_cycles = plt.subplots(1, 1, sharex=True, figsize=(7,5))
for label, battery_col, ls, output_file in zip(labels, battery_cols, linestyles, output_files):
    # Read the Hercules output file
    df = pd.read_csv(output_file, index_col=False)

    power_ref_input = df["external_signals.plant_power_reference"] / 1e3

    # Extract individual components powers as well as total power
    n_wind_turbines = 2
    wind_power = df[["hercules_comms.amr_wind.wind_farm_0.turbine_powers.{0:03d}".format(t)
                     for t in range(n_wind_turbines)]].to_numpy().sum(axis=1) / 1e3
    battery_power = -df["py_sims.battery_0.outputs.power"] / 1e3 # discharging positive

    power_output = df["py_sims.inputs.locally_generated_power"] / 1e3 + battery_power

    time = df["hercules_comms.amr_wind.wind_farm_0.sim_time_s_amr_wind"] / 60 # minutes

    # Calculate RMSE for power reference
    rmse = np.sqrt(np.mean((power_output-power_ref_input)**2))
    print('RMSE of {0} controller: {1:.2f} MW'.format(label, rmse))

    # Plotting power outputs from each technology as well as the total power output (top)
    # Plotting the SOC of the battery (bottom)
    fig, ax = plt.subplots(1, 1, sharex=True, figsize=(7,5))
    ax.plot(time, wind_power, label="Wind", color=wind_col)
    ax.plot(time, battery_power, label="Battery", color=battery_col, ls=ls)
    ax.plot(time, power_output, label="Plant output", color=plant_col)
    ax.plot(time, power_ref_input, 'k--', label="Reference")
    ax.set_ylabel("Power [MW]")
    ax.set_xlabel("Time [mins]")
    ax.grid()
    ax.legend(loc="best")
    ax.text(15, 4, "RMSE = {0:.2f} MW".format(rmse), fontsize=12)
    ax.set_xlim([-0.5, 20.5])
    ax.set_ylim([-3, 11])
    ax.set_title("Plant behavior with {0} battery controller".format(label))

    # Plot to compare battery behavior 
    battery_soc = df["py_sims.battery_0.outputs.soc"]
    ax_tracking[0].plot(time, battery_power, color=battery_col, label=label, ls=ls)
    ax_tracking[1].plot(time, battery_soc, color=battery_col, label=label, ls=ls)

    battery_cycle_count = df["py_sims.battery_0.outputs.total_cycles"]
    ax_cycles.plot(time, battery_cycle_count, color=battery_col, label=label, ls=ls)
    
# Plot labels etc
ax_tracking[0].set_title("Battery Power and SOC Comparison")
ax_tracking[0].legend()
ax_tracking[0].grid()
ax_tracking[1].grid()
ax_tracking[0].set_ylabel("Battery power [MW]")
ax_tracking[1].set_ylabel("Battery SOC")
ax_tracking[1].set_xlabel("Time [mins]")

ax_cycles.set_title("Battery Cycle Comparison")
ax_cycles.set_xlabel("Time [mins]")
ax_cycles.grid()
ax_cycles.legend()
ax_cycles.set_ylabel("Cycle Count [-]")

plt.show()
