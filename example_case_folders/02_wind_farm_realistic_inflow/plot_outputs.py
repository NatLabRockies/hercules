# Plot the outputs of the simulation

import matplotlib.pyplot as plt
import pandas as pd

# Read the Hercules output file
df = pd.read_csv("outputs/hercules_output.csv", index_col=False)

# Limit to the first 4 hours
df = df.iloc[: 3600 * 4]

print(df["py_sims.wind_farm_0.outputs.floris_wind_direction"].head())

# Set number of turbines
turbines_to_plot = [0, 8]

# Define a consistent color map with 9
colors = [
    "tab:blue",
    "tab:orange",
    "tab:green",
    "tab:red",
    "tab:purple",
    "tab:brown",
    "tab:pink",
    "tab:gray",
    "tab:olive",
]

fig, axarr = plt.subplots(2, 1, sharex=True)

# Plot the wind speeds
ax = axarr[0]
for t_idx in turbines_to_plot:
    ax.plot(
        df["time"],
        df[f"py_sims.wind_farm_0.outputs.unwaked_velocity.{t_idx:03}"],
        label=f"Unwaked {t_idx}",
        color=colors[t_idx],
    )
for t_idx in turbines_to_plot:
    ax.plot(
        df["time"],
        df[f"py_sims.wind_farm_0.outputs.waked_velocity.{t_idx:03}"],
        label=f"Waked {t_idx}",
        linestyle="--",
        color=colors[t_idx],
    )

# Plot the FLORIS wind speed
ax.plot(
    df["time"],
    df["py_sims.wind_farm_0.outputs.floris_wind_speed"],
    label="FLORIS",
    color="black",
    lw=2,
)

ax.grid(True)
ax.legend()
ax.set_ylabel("Wind Speed [m/s]")


# Plot the power
ax = axarr[1]
for t_idx in turbines_to_plot:
    ax.plot(
        df["time"],
        df[f"py_sims.wind_farm_0.outputs.power.{t_idx:03}"],
        label=f"Turbine {t_idx}",
        color=colors[t_idx],
    )
for t_idx in turbines_to_plot:
    ax.plot(
        df["time"],
        df[f"py_sims.inputs.derating_{t_idx:03d}"],
        label=f"Derating {t_idx}",
        linestyle="--",
        color=colors[t_idx],
    )
ax.grid(True)
ax.legend()
ax.set_xlabel("Time [s]")
ax.set_ylabel("Power [kW]")
plt.show()
