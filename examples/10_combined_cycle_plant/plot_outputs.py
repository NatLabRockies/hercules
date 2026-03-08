# Plot the outputs of the simulation for the OCGT example

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
ax.plot(time_minutes, df["combined_cycle_plant.power"] / 1000, label="Power Output", color="k")
ax.plot(
    time_minutes,
    df["combined_cycle_plant.OCGT.power_setpoint"] / 1000,
    label="Power Setpoint (OCGT)",
    color="r",
    linestyle="--",
)
ax.plot(
    time_minutes,
    df["combined_cycle_plant.ST.power_setpoint"] / 1000,
    label="Power Setpoint (ST)",
    color="b",
    linestyle="--",
)
ax.plot(
    time_minutes,
    df["combined_cycle_plant.OCGT.power"] / 1000,
    label="Power Output (OCGT)",
    color="r",
)
ax.plot(
    time_minutes,
    df["combined_cycle_plant.ST.power"] / 1000,
    label="Power Output (ST)",
    color="b",
)

ax = axarr[1]
ax.plot(
    time_minutes,
    df["combined_cycle_plant.OCGT.state"],
    label="State (OCGT)",
    color="r",
    linestyle="-",
)
ax.plot(
    time_minutes,
    df["combined_cycle_plant.ST.state"],
    label="State (ST)",
    color="b",
    linestyle="-",
)

ax.set_ylabel("State")
ax.set_yticks([0, 1, 2, 3, 4, 5])
ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
ax.set_title(
    "Turbine State (0=Off, 1=Hot Starting, 2=Warm Starting, 3=Cold Starting, 4=On, 5=Stopping)"
)
ax.grid(True)

# ax.axhline(
#     h_dict["thermal_power_plant"]["rated_capacity"] / 1000,
#     color="gray",
#     linestyle=":",
#     label="Rated Capacity",
# )
# ax.axhline(
#     h_dict["thermal_power_plant"]["min_stable_load_fraction"]
#     * h_dict["thermal_power_plant"]["rated_capacity"]
#     / 1000,
#     color="gray",
#     linestyle="--",
#     label="Minimum Stable Load",
# )
# ax.set_ylabel("Power [MW]")
# ax.set_title("Open Cycle Gas Turbine Power Output")
# ax.legend()
# ax.grid(True)

# # Plot the state
# ax = axarr[1]
# ax.plot(time_minutes, df["thermal_power_plant.state"], label="State", color="k")
# ax.set_ylabel("State")
# ax.set_yticks([0, 1, 2, 3, 4, 5])
# ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
# ax.set_title(
#     "Turbine State (0=Off, 1=Hot Starting, 2=Warm Starting, 3=Cold Starting, 4=On, 5=Stopping)"
# )
# ax.grid(True)

# # Plot the efficiency
# ax = axarr[2]
# ax.plot(
#     time_minutes,
#     df["thermal_power_plant.efficiency"] * 100,
#     label="Efficiency",
#     color="g",
# )
# ax.set_ylabel("Efficiency [%]")
# ax.set_title("Thermal Efficiency")
# ax.grid(True)

# # Plot the fuel consumption
# ax = axarr[3]
# ax.plot(
#     time_minutes,
#     df["thermal_power_plant.fuel_volume_rate"],
#     label="Fuel Volume Rate",
#     color="orange",
# )
# ax.set_ylabel("Fuel [m³/s]")
# ax.set_title("Fuel Volume Rate")
# ax.grid(True)

# ax.set_xlabel("Time [minutes]")

plt.tight_layout()
plt.show()
