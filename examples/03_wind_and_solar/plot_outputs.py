# Plot the outputs of the simulation

import matplotlib.pyplot as plt
import pandas as pd

# Read the Hercules output file
df = pd.read_csv("outputs/hercules_output.csv", index_col=False)


fig, axarr = plt.subplots()  # 2, 1, sharex=True)

# Plot the wind farm power
ax = axarr
ax.plot(
    df["time"],
    df["wind_farm.power"],
    label="Wind Farm",
)

ax.plot(
    df["time"],
    df["solar_farm.power"],
    label="Solar PV",
)

ax.plot(
    df["time"],
    df["plant.power"],
    label="Total",
    color="k",
)

ax.grid(True)
ax.legend()
ax.set_xlabel("Time [s]")
ax.set_ylabel("Power [kW]")

plt.show()
