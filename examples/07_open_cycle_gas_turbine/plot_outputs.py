# Plot the outputs of the simulation for the OCGT example

import matplotlib.pyplot as plt
from hercules import HerculesOutput

# Read the Hercules output file using HerculesOutput
ho_ocgt = HerculesOutput("outputs/hercules_output_ocgt.h5")
ho_ccgt = HerculesOutput("outputs/hercules_output_ccgt.h5")

# Print metadata information
print("Simulation Metadata:")
ho_ocgt.print_metadata()
print()

# Create a shortcut to the dataframe
df_ocgt = ho_ocgt.df
df_ccgt = ho_ccgt.df

col_ocgt = "darkred"
col_ccgt = "darkblue"

# Get the h_dict from metadata
h_dict_ocgt = ho_ocgt.h_dict
h_dict_ccgt = ho_ccgt.h_dict

# Convert time to minutes for easier reading
time_hours_ocgt = df_ocgt["time"] / 60 / 60
time_hours_ccgt = df_ccgt["time"] / 60 / 60

fig, axarr = plt.subplots(4, 1, sharex=True, figsize=(10, 10))

# Plot the power output and setpoint
ax = axarr[0]
ax.axhline(
    h_dict_ocgt["open_cycle_gas_turbine"]["rated_capacity"] / 1000,
    color="gray",
    linestyle=":",
    label="Rated capacity (both)",
)
ax.axhline(
    h_dict_ocgt["open_cycle_gas_turbine"]["min_stable_load_fraction"]
    * h_dict_ocgt["open_cycle_gas_turbine"]["rated_capacity"]
    / 1000,
    color=col_ocgt,
    linestyle=":",
    label="OCGT min. stable load",
)
ax.axhline(
    h_dict_ccgt["combined_cycle_gas_turbine"]["min_stable_load_fraction"]
    * h_dict_ccgt["combined_cycle_gas_turbine"]["rated_capacity"]
    / 1000,
    color=col_ccgt,
    linestyle=":",
    label="CCGT min. stable load",
)
ax.plot(
    time_hours_ocgt,
    df_ocgt["open_cycle_gas_turbine.power_setpoint"] / 1000,
    label="Power setpoint",
    color="k",
    linestyle="--",
)
ax.plot(
    time_hours_ocgt,
    df_ocgt["open_cycle_gas_turbine.power"] / 1000,
    label="OCGT output",
    color=col_ocgt,
)
ax.plot(
    time_hours_ccgt,
    df_ccgt["combined_cycle_gas_turbine.power"] / 1000,
    label="CCGT output",
    color=col_ccgt,
    linestyle="-.",
)
ax.set_ylabel("Power [MW]")
ax.legend(loc="upper right")
ax.grid(True)

# Plot the state
ax = axarr[1]
ax.plot(
    time_hours_ocgt, df_ocgt["open_cycle_gas_turbine.state"], label="OCGT State", color=col_ocgt
)
ax.plot(
    time_hours_ccgt,
    df_ccgt["combined_cycle_gas_turbine.state"],
    label="CCGT State",
    color=col_ccgt,
    linestyle="-.",
)
ax.set_ylabel("State")
ax.set_yticks([0, 1, 2, 3, 4, 5])
ax.set_yticklabels(["Off", "Hot Starting", "Warm Starting", "Cold Starting", "On", "Stopping"])
ax.legend(loc="upper right")
ax.grid(True)

# Plot the efficiency
ax = axarr[2]
ax.plot(
    time_hours_ocgt,
    df_ocgt["open_cycle_gas_turbine.efficiency"] * 100,
    label="OCGT Efficiency",
    color=col_ocgt,
)
ax.plot(
    time_hours_ccgt,
    df_ccgt["combined_cycle_gas_turbine.efficiency"] * 100,
    label="CCGT Efficiency",
    color=col_ccgt,
    linestyle="-.",
)
ax.legend(loc="upper right")
ax.set_ylim(0, 100)
ax.set_ylabel("Efficiency [%]")
ax.set_title("Thermal Efficiency")
ax.grid(True)

# Plot the fuel consumption
ax = axarr[3]
ax.plot(
    time_hours_ocgt,
    df_ocgt["open_cycle_gas_turbine.fuel_volume_rate"],
    label="OCGT Fuel Volume Rate",
    color=col_ocgt,
)
ax.plot(
    time_hours_ccgt,
    df_ccgt["combined_cycle_gas_turbine.fuel_volume_rate"],
    label="CCGT Fuel Volume Rate",
    color=col_ccgt,
    linestyle="-.",
)
ax.legend(loc="upper right")
ax.set_ylabel("Fuel [m³/s]")
ax.set_title("Fuel Volume Rate")
ax.grid(True)

ax.set_xlabel("Time [hours]")
ax.set_xlim(0, 10)

plt.tight_layout()
plt.show()
