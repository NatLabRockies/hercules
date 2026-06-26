# Plot the outputs of the simulation for the OCGT example

import matplotlib.pyplot as plt
from hercules import HerculesOutput

# Read the Hercules output file using HerculesOutput
ho = HerculesOutput("outputs_07/hercules_output.h5")

# Print metadata information
print("Simulation Metadata:")
ho.print_metadata()
print()

# Create a shortcut to the dataframe
df = ho.df

# Get the h_dict from metadata
h_dict = ho.h_dict
component_name = h_dict["component_names"][0]

# Convert time to minutes for easier reading
time_minutes = df["time"] / 60

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Plot the power output and setpoint
ax = axarr[0]
ax.plot(time_minutes, df[f"{component_name}.power"] / 1000, label="Power Output", color="b")
ax.plot(
    time_minutes,
    df[f"{component_name}.power_setpoint"] / 1000,
    label="Power Setpoint",
    color="r",
    linestyle="--",
)
ax.axhline(
    h_dict[component_name]["rated_capacity"] / 1000,
    color="gray",
    linestyle=":",
    label="Rated Capacity",
)
ax.axhline(
    h_dict[component_name]["min_stable_load_fraction"]
    * h_dict[component_name]["rated_capacity"]
    / 1000,
    color="gray",
    linestyle="--",
    label="Minimum Stable Load",
)
ax.set_ylabel("Power [MW]")
ax.set_title("Thermal Power Plant Output")
ax.legend()
ax.grid(True)

# Plot the state
ax = axarr[1]
ax.plot(time_minutes, df[f"{component_name}.state"], label="State", color="k")
ax.set_ylabel("State")
ax.set_yticks([0, 1, 2, 3, 4, 5, 6, 7])
ax.set_yticklabels(
    [
        "Off (Cold)",
        "Cold Starting",
        "Off (Warm)",
        "Warm Starting",
        "Off (Hot)",
        "Hot Starting",
        "On",
        "Stopping",
    ]
)
ax.set_title("Turbine State")
ax.grid(True)

# Plot the efficiency
ax = axarr[2]
ax.plot(
    time_minutes,
    df[f"{component_name}.efficiency"] * 100,
    label="Efficiency",
    color="g",
)
ax.set_ylabel("Efficiency [%]")
ax.set_title("Thermal Efficiency")
ax.grid(True)

# Plot the fuel consumption
ax = axarr[3]
ax.plot(
    time_minutes,
    df[f"{component_name}.fuel_volume_rate"],
    label="Fuel Volume Rate",
    color="orange",
)
ax.set_ylabel("Fuel [m³/s]")
ax.set_title("Fuel Volume Rate")
ax.grid(True)

ax.set_xlabel("Time [minutes]")

plt.tight_layout()
plt.show()
