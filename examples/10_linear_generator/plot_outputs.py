# Plot the outputs of the simulation for the linear generator example

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

# Get the h_dict from metadata
h_dict = ho.h_dict

# Convert time to minutes for easier reading
time_minutes = df["time"] / 60

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Plot the power output and setpoint
ax = axarr[0]
ax.plot(time_minutes, df["linear_generator.power"], label="Power Output", color="b")
ax.plot(
    time_minutes,
    df["linear_generator.power_setpoint"],
    label="Power Setpoint",
    color="r",
    linestyle="--",
)
ax.axhline(
    h_dict["linear_generator"]["rated_capacity"],
    color="gray",
    linestyle=":",
    label="Rated Capacity",
)
ax.set_ylabel("Power [kW]")
ax.set_title("Linear Generator Power Output")
ax.legend()
ax.grid(True)

# Plot the state
ax = axarr[1]
ax.plot(time_minutes, df["linear_generator.state"], label="State", color="k")
ax.set_ylabel("State")
ax.set_yticks([0, 1, 2, 3, 4, 5])
ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
ax.set_title(
    "Generator State (0=Off, 1=Hot Starting, 2=Warm Starting, 3=Cold Starting, 4=On, 5=Stopping)"
)
ax.grid(True)

# Plot the efficiency
ax = axarr[2]
ax.plot(
    time_minutes,
    df["linear_generator.efficiency"] * 100,
    label="Efficiency",
    color="g",
)
ax.set_ylabel("Efficiency [%]")
ax.set_title("Thermal Efficiency (flat across all load levels)")
ax.grid(True)

# Plot the fuel consumption
ax = axarr[3]
ax.plot(
    time_minutes,
    df["linear_generator.fuel_volume_rate"],
    label="Fuel Volume Rate",
    color="orange",
)
ax.set_ylabel("Fuel [m³/s]")
ax.set_title("Fuel Volume Rate")
ax.grid(True)

ax.set_xlabel("Time [minutes]")

plt.tight_layout()
plt.show()
