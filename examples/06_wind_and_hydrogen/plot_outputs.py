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

# Set number of turbines
turbines_to_plot = [0, 1, 2, 3, 4, 5, 6, 7, 8]

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


fig, axarr = plt.subplots(4, 1, sharex=True)


# Plot wind resource
ax = axarr[0]

# Plot the FLORIS wind speed
ax.plot(
    df["time_utc"],
    df["wind_farm.wind_speed_mean_background"],
    label="Mean Unwaked Wind Speed",
    color="black",
    lw=2,
)
ax.grid(True)
ax.legend()
ax.set_ylabel("Wind Speed [m/s]")

# Plot the turbine powers
ax = axarr[1]
for t_idx in turbines_to_plot:
    ax.plot(
        df["time_utc"],
        df[f"wind_farm.turbine_powers.{t_idx:03}"],
        label=f"Turbine {t_idx}",
        color=colors[t_idx],
    )
ax.set_ylabel("Power [kW]")

# Plot the hybrid plant power
ax = axarr[2]
ax.plot(
    df["time_utc"],
    df["wind_farm.power"],
    label="Wind Power",
    color="b",
    alpha=0.75,
)
ax.plot(
    df["time_utc"],
    df["electrolyzer.power_input_kw"],
    label="Electrolyzer Input Power",
    color="r",
    alpha=0.75,
)
ax.fill_between(
    df["time_utc"],
    -df["electrolyzer.power"],
    label="Electrolzyer Power Used",
    color="b",
    alpha=0.5,
)

ax.set_ylabel("Power [kW]")

# Plot hydrogen output
ax = axarr[3]
ax.plot(
    df["time_utc"], df["external_signals.hydrogen_reference"], label="Hydrogen Reference", color="k"
)
ax.set_ylabel("Hydrogen production [kg]")
ax.plot(df["time_utc"], df["electrolyzer.H2_mfr"], label="Hydrogen Output", color="b")

ax.set_xlabel("Time [s]")

for ax in axarr:
    ax.grid(True)
    ax.legend()


plt.show()
