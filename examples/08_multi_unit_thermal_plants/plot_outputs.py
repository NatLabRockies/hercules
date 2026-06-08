# Plot the outputs of the simulation for the OCGT example

import matplotlib.pyplot as plt
from hercules import HerculesOutput

# Read the Hercules output file using HerculesOutput
ho = HerculesOutput("outputs/hercules_output.h5")

# Print metadata information
ho.print_metadata()

# Create a shortcut to the dataframe
df = ho.df

# Get the h_dict from metadata
h_dict = ho.h_dict

component_name = h_dict["component_names"][0]
unit_names = h_dict[component_name]["unit_names"]

# Convert time to minutes for easier reading
time_minutes = df["time"] / 60

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Plot the power output and setpoint
ax = axarr[0]
ax.plot(time_minutes, df[f"{component_name}.power"] / 1000, label="Power Output", color="k")
for k, unit_name in enumerate(unit_names):
    ax = axarr[0]
    ax.plot(
        time_minutes,
        df[f"{component_name}.{unit_name}.power_setpoint"] / 1000,
        label=f"Power setpoint ({unit_name})",
        color="C" + str(k),
        linestyle="--",
    )
    ax.plot(
        time_minutes,
        df[f"{component_name}.{unit_name}.power"] / 1000,
        label=f"Power output ({unit_name})",
        color="C" + str(k),
    )
    ax.axhline(
        h_dict[component_name][unit_name]["rated_capacity"] / 1000,
        color="gray",
        linestyle=":",
        label="Unit rated capacity",
    )

    # Plot the state of each unit
    ax = axarr[1]
    ax.plot(
        time_minutes, df[f"{component_name}.{unit_name}.state"], label=unit_name, color="C" + str(k)
    )
    ax.set_ylabel("State")
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
    ax.grid(True)
    ax.legend()

ax = axarr[0]
ax.axhline(
    h_dict[component_name]["rated_capacity"] / 1000,
    color="black",
    linestyle=":",
    label="Plant rated capacity",
)
ax.set_ylabel("Power [MW]")
ax.legend()
ax.grid(True)
ax.set_xlim(0, time_minutes.iloc[-1])

# Plot the efficiency of each unit
ax = axarr[2]
try:
    for k, unit_name in enumerate(unit_names):
        ax.plot(
            time_minutes,
            df[f"{component_name}.{unit_name}.efficiency"] * 100,
            label=unit_name,
            color="C" + str(k),
        )
except KeyError:
    ax.plot(time_minutes, df[f"{component_name}.efficiency"] * 100, label="Efficiency", color="g")

ax.set_ylabel("Thermal efficiency [%]")
ax.grid(True)
ax.legend()

# Fuel consumption
ax = axarr[3]
try:
    for k, unit_name in enumerate(unit_names):
        ax.plot(
            time_minutes,
            df[f"{component_name}.{unit_name}.fuel_volume_rate"],
            label=unit_name,
            color="C" + str(k),
        )
except KeyError:
    ax.plot(
        time_minutes,
        df[f"{component_name}.fuel_volume_rate"],
        label="Fuel Volume Rate",
        color="orange",
    )
ax.set_ylabel("Fuel [m³/s]")
ax.grid(True)
ax.legend()

plt.tight_layout()
plt.show()
