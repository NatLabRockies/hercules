# Plot the outputs of the simulation

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

# Convert time to minutes for easier reading
time_minutes = df["time"] / 60

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Plot the power output and setpoint
ax = axarr[0]
ax.plot(time_minutes, df["thermal_power_plant.power"] / 1000, label="Power Output", color="k")
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT1.power_setpoint"] / 1000,
    label="Power setpoint (OCGT1)",
    color="r",
    linestyle="--",
)
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT2.power_setpoint"] / 1000,
    label="Power setpoint (OCGT2)",
    color="b",
    linestyle="--",
)
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT3.power_setpoint"] / 1000,
    label="Power setpoint (OCGT3)",
    color="g",
    linestyle="--",
)
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT1.power"] / 1000,
    label="Power output (OCGT1)",
    color="r",
)
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT2.power"] / 1000,
    label="Power output (OCGT2)",
    color="b",
)
ax.plot(
    time_minutes,
    df["thermal_power_plant.OCGT3.power"] / 1000,
    label="Power output (OCGT3)",
    color="g",
)
ax.axhline(
    h_dict["thermal_power_plant"]["rated_capacity"] / 1000,
    color="black",
    linestyle=":",
    label="Plant rated capacity",
)
ax.axhline(
    h_dict["thermal_power_plant"]["OCGT1"]["rated_capacity"] / 1000,
    color="gray",
    linestyle=":",
    label="Unit rated capacity",
)
ax.set_ylabel("Power [MW]")
ax.legend()
ax.grid(True)
ax.set_xlim(0, time_minutes.iloc[-1])

# Plot the state of each unit
ax = axarr[1]
ax.plot(time_minutes, df["thermal_power_plant.OCGT1.state"], label="OCGT1", color="r")
ax.plot(time_minutes, df["thermal_power_plant.OCGT2.state"], label="OCGT2", color="b")
ax.plot(time_minutes, df["thermal_power_plant.OCGT3.state"], label="OCGT3", color="g")
ax.set_ylabel("State")
ax.set_yticks([0, 1, 2, 3, 4, 5])
ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
ax.grid(True)
ax.legend()

# Plot the efficiency of each unit
ax = axarr[2]
ax.plot(time_minutes, df["thermal_power_plant.OCGT1.efficiency"] * 100, label="OCGT1", color="r")
ax.plot(time_minutes, df["thermal_power_plant.OCGT2.efficiency"] * 100, label="OCGT2", color="b")
ax.plot(time_minutes, df["thermal_power_plant.OCGT3.efficiency"] * 100, label="OCGT3", color="g")
ax.set_ylabel("Thermal efficiency [%]")
ax.grid(True)
ax.legend()

# Fuel consumption
ax = axarr[3]
ax.plot(time_minutes, df["thermal_power_plant.OCGT1.fuel_volume_rate"], label="OCGT1", color="r")
ax.plot(time_minutes, df["thermal_power_plant.OCGT2.fuel_volume_rate"], label="OCGT2", color="b")
ax.plot(time_minutes, df["thermal_power_plant.OCGT3.fuel_volume_rate"], label="OCGT3", color="g")
ax.set_ylabel("Fuel [m³/s]")
ax.grid(True)
ax.legend()
ax.set_xlabel("Time [mins]")

plt.tight_layout()
plt.show()
