# Plot the outputs of the simulation

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


_, ax = plt.subplots(1, 1, sharex=True)


# Plot the power
ax.plot(
    df["time_utc"],
    df["power_unit_1.power"],
    label="Power Playback of Power Unit 1",
    color="tab:blue",
)


ax.grid(True)
ax.legend()
ax.set_xlabel("Time (UTC)")
ax.set_ylabel("Power [kW]")
plt.show()
