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

# Set number of turbines
n_turbines = 3

# Define a consistent color map with 3 entries
colors = ["tab:blue", "tab:orange", "tab:green"]

fig, ax = plt.subplots(1, 1, sharex=True)


# Plot the power
for t_idx in range(3):
    if f"wind_farm.turbine_powers.{t_idx:03}" in df.columns:
        ax.plot(
            df["time"],
            df[f"wind_farm.turbine_powers.{t_idx:03}"],
            label=f"Turbine {t_idx}",
            color=colors[t_idx],
        )

# Check if derating columns exist and plot them if they do
for t_idx in range(3):
    if f"wind_farm.turbine_power_setpoints.{t_idx:03}" in df.columns:
        ax.plot(
            df["time"],
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
