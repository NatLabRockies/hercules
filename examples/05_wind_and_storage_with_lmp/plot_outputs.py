# Plot the outputs of the simulation for the wind, storage, and LMP example

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

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Get an index of where battery power is positive or negative
df_battery_positive = df.copy()
df_battery_negative = df.copy()

# 0 negative power from df_battery_positive and vice versa
df_battery_positive.loc[df_battery_positive["battery.power"] < 0, "battery.power"] = 0
df_battery_negative.loc[df_battery_negative["battery.power"] > 0, "battery.power"] = 0

# Plot the farm power
ax = axarr[0]

# Plot the hybrid plant power
ax.plot(
    df["time"] / 3600,
    df["wind_farm.power"],
    label="Wind Power",
    color="b",
    alpha=0.5,
)

# Only plot battery discharging if there are any positive battery power values

ax.fill_between(
    df_battery_positive["time"] / 3600,
    df_battery_positive["wind_farm.power"],
    df_battery_positive["wind_farm.power"] + df_battery_positive["battery.power"],
    label="Battery Discharging",
    color="orange",
    alpha=0.5,
)

# Only plot battery charging if there are any negative battery power values

ax.fill_between(
    df_battery_negative["time"] / 3600,
    df_battery_negative["wind_farm.power"],
    df_battery_negative["wind_farm.power"] + df_battery_negative["battery.power"],
    label="Battery Charging",
    color="green",
    alpha=0.5,
)

# Plot total hybrid plant power (wind + battery)
ax.plot(
    df["time"] / 3600,
    df["wind_farm.power"] + df["battery.power"],
    label="Hybrid Plant Total",
    color="k",
)
ax.axhline(
    h_dict["plant"]["interconnect_limit"], color="r", linestyle="--", label="Interconnect Limit"
)


ax.set_ylabel("Power [kW]")
ax.legend()
ax.grid(True)

# Plot the battery SOC
ax = axarr[1]

ax.plot(df["time"] / 3600, df["battery.soc"], label="Battery SOC", color="k")
ax.axhline(h_dict["battery"]["max_SOC"], color="r", linestyle="--", label="Max SOC")
ax.axhline(h_dict["battery"]["min_SOC"], color="r", linestyle="--", label="Min SOC")
ax.set_ylabel("SOC")
ax.legend()
ax.grid(True)

# Plot the battery power and power setpoint
ax = axarr[2]
ax.plot(df["time"] / 3600, df["battery.power"], label="Battery Power", color="k")
ax.plot(df["time"] / 3600, df["battery.power_setpoint"], label="Battery Power Setpoint", color="r")

ax.set_ylabel("Power [kW]")
ax.legend()
ax.grid(True)

# Plot the LMP data
ax = axarr[3]
# Plot lmp_rt from HDF5 output (this was logged)
if "external_signals.lmp_rt" in df.columns:
    ax.plot(df["time"] / 3600, df["external_signals.lmp_rt"], label="LMP RT (logged)", color="b")


ax.axhline(15, color="green", linestyle=":", label="Charge Threshold ($15)")
ax.axhline(35, color="orange", linestyle=":", label="Discharge Threshold ($35)")

ax.set_xlabel("Time [hr]")
ax.set_ylabel("LMP [$/MWh]")
ax.legend()
ax.grid(True)

plt.tight_layout()
plt.show()
