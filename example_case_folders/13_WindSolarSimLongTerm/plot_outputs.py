# Plot the outputs of the simulation

import matplotlib.pyplot as plt
import pandas as pd

# Read the Hercules output file
df = pd.read_csv("outputs/hercules_output.csv", index_col=False)

# Set number of turbines
n_turbines = 3

fig, axarr = plt.subplots(sharex=True)  # 2, 1, sharex=True)

# Plot the power
ax = axarr
for t_idx in range(3):
    ax.plot(
        df["time"],
        df[f"py_sims.wind_farm_0.outputs.power.{t_idx:03}"],
        label=f"Turbine {t_idx}",
    )

ax.plot(
    df["time"],
    df["py_sims.solar_farm_0.outputs.power_mw"] * 1000,
    label="Solar PV",
)

total_power = df["py_sims.solar_farm_0.outputs.power_mw"] * 1000
for t_idx in range(3):
    total_power = total_power + df[f"py_sims.wind_farm_0.outputs.power.{t_idx:03}"]

ax.plot(
    df["time"],
    total_power,
    label="Total",
    color="k",
)

ax.grid(True)
ax.legend()
ax.set_xlabel("Time [s]")
ax.set_ylabel("Power [kW]")

plt.show()
