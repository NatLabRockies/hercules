# Plot the outputs of the simulation for the wind and storage example

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
print(h_dict.keys())
print(h_dict["electrolyzer"].keys())
print(h_dict["external_data_file"])


fig, axarr = plt.subplots(2, 1, sharex=True)

# Get an index of where battery power is postive or negative
df_battery_positive = df.copy()
df_battery_negative = df.copy()

# 0 negative power from df_battery_positive and vice versa

# Plot the farm power
ax = axarr[0]

# Plot the hybrid plant power
ax.plot(
    df["time"],
    df["wind_farm.power"],
    label="Wind Power",
    color="b",
    alpha=0.75,
)
ax.plot(
    df["time"],
    df["electrolyzer.power_input_kw"],
    label="Electrolyzer Input Power",
    color="r",
    alpha=0.75,
)
ax.fill_between(
    df["time"],
    -df["electrolyzer.power"],
    label="Electrolzyer Power Used",
    color="b",
    alpha=0.5,
)

# # Only plot battery discharging if there are any positive battery power values

# ax.fill_between(
#     df_battery_positive["time"],
#     0,
#     df_battery_positive["wind_farm.power"] + df_battery_positive["battery.power"],
#     label="Battery Discharging",
#     color="orange",
#     alpha=0.5,
# )

# # Only plot battery charging if there are any negative battery power values

# ax.fill_between(
#     df_battery_negative["time"],
#     df_battery_negative["wind_farm.power"],
#     df_battery_negative["wind_farm.power"] + df_battery_negative["battery.power"],
#     label="Battery Charging",
#     color="green",
#     alpha=0.5,
# )

# # Plot total hybrid plant power (wind + battery)
# ax.plot(
#     df["time"],
#     df["wind_farm.power"] + df["battery.power"],
#     label="Hybrid Plant Total",
#     color="k",
# )
# ax.axhline(
#     h_dict["plant"]["interconnect_limit"], color="r", linestyle="--", label="Interconnect Limit"
# )


ax.set_ylabel("Power [kW]")

# Plot hydrogen output
ax = axarr[1]
ax.plot(df["time"], df["external_signals.hydrogen_reference"], label="Hydrogen Reference", 
        color="k")
ax.set_ylabel("Hydrogen production [kg]")
ax.plot(df["time"], df["electrolyzer.H2_mfr"], label="Hydrogen Output", color="b")

# # Plot the battery power and power setpoint
# ax = axarr[2]
# ax.plot(df["time"], df["battery.power"], label="Battery Power", color="k")
# ax.plot(df["time"], df["battery.power_setpoint"], label="Battery Power Setpoint", color="r")

# ax.set_xlabel("Time [s]")
# ax.set_ylabel("Power [kW]")

for ax in axarr:
    ax.grid(True)
    ax.legend()


plt.show()
