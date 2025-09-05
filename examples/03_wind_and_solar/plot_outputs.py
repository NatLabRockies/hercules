# Plot the outputs of the simulation for the wind and solar example

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


fig, ax = plt.subplots()

# Plot the hybrid plant power

ax.fill_between(
    df["time"],
    0,
    df["wind_farm.power"],
    label="Wind Power",
    color="b",
    alpha=0.5,
)
ax.fill_between(
    df["time"],
    df["wind_farm.power"],
    df["wind_farm.power"] + df["solar_farm.power"],
    label="Solar Power",
    color="orange",
    alpha=0.5,
)
ax.plot(
    df["time"],
    df["wind_farm.power"] + df["solar_farm.power"],
    label="Hybrid Plant",
    color="k",
)
ax.axhline(
    h_dict["plant"]["interconnect_limit"], color="r", linestyle="--", label="Interconnect Limit"
)

ax.grid(True)
ax.legend()
ax.set_xlabel("Time [s]")
ax.set_ylabel("Power [kW]")


plt.show()
