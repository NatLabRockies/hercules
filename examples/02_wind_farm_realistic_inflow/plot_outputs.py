# Plot the outputs of the simulation

import matplotlib.pyplot as plt
from hercules import HerculesOutput

# Read the Hercules output file using HerculesOutput
ho = HerculesOutput("outputs/hercules_output.h5")

# Print metadata information
print("Simulation Metadata:")
ho.print_metadata()
print()

# Create a shortcut to the dataframe
df = ho.df

# Limit to the first 4 hours
# df = df.iloc[: 3600 * 4]

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
        df["time_utc"],
        df[f"wind_farm.wind_speeds_background.{t_idx:03}"],
        label=f"Unwaked {t_idx}",
        color=colors[t_idx],
    )
for t_idx in turbines_to_plot:
    ax.plot(
        df["time_utc"],
        df[f"wind_farm.wind_speeds_withwakes.{t_idx:03}"],
        label=f"Waked {t_idx}",
        linestyle="--",
        color=colors[t_idx],
    )


ax.grid(True)
ax.legend()
ax.set_ylabel("Wind Speed [m/s]")


# Plot the power
ax = axarr[1]
for t_idx in turbines_to_plot:
    ax.plot(
        df["time_utc"],
        df[f"wind_farm.turbine_powers.{t_idx:03}"],
        label=f"Turbine {t_idx}",
        color=colors[t_idx],
    )
for t_idx in turbines_to_plot:
    ax.plot(
        df["time_utc"],
        df[f"wind_farm.turbine_power_setpoints.{t_idx:03}"],
        label=f"Power Setpoint {t_idx}",
        linestyle="--",
        color=colors[t_idx],
    )
ax.grid(True)
ax.legend()
ax.set_xlabel("Time [s]")
ax.set_ylabel("Power [kW]")
plt.show()
