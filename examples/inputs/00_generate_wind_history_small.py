# # Generate wind history for a small farm for early examples
# Generate a small demonstration wind history using the example FLORIS model
import floris.layout_visualization as layoutviz
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from floris import FlorisModel

show_plots = False

# ## Parameters
dt = 1.0  # Sampling interval [s]
N = 1000  # Number of time steps
delay = 5  # Delay between upstream and downstream turbines [s]

# Read FLORIS model input
fmodel = FlorisModel("floris_input_small.yaml")


# ## Show the layout
fig, ax = plt.subplots()
layoutviz.plot_turbine_points(fmodel, ax=ax)
layoutviz.plot_turbine_labels(fmodel, ax=ax)
layoutviz.plot_waking_directions(fmodel, ax=ax)
ax.set_title("Example farm layout")


# ## Generate the histories
# Set random seed for reproducibility
np.random.seed(1)

# Generate overall wind speeds and directions using a random walk
ws_u_inf = 8.0 * np.ones(N + delay)
wd_inf = 270.0 * np.ones(N + delay)

for i in range(1, N + delay):
    # Add a small perturbation to wind speed
    ws_u_inf[i] = ws_u_inf[i - 1] + 0.1 * np.random.randn()
    # To enable a drifting wind direction, uncomment the next line:
    # wd_inf[i] = wd_inf[i - 1] + 1.0 * np.random.randn()

    # Limit variables to physical ranges
    if ws_u_inf[i] < 0.0:
        ws_u_inf[i] = 0.0
    if ws_u_inf[i] > 13.0:
        ws_u_inf[i] = 13.0
    if wd_inf[i] < 0.0:
        wd_inf[i] = 360.0 + wd_inf[i]
    if wd_inf[i] > 360.0:
        wd_inf[i] = wd_inf[i] - 360.0

# Plot the ambient histories
fig, axarr = plt.subplots(2, 1, sharex=True)
axarr[0].plot(ws_u_inf, color="k")
axarr[0].set_ylabel("Wind speed [m/s]")
axarr[1].plot(wd_inf, color="k")
axarr[1].set_ylabel("Wind direction [deg]")
axarr[1].set_xlabel("Time step")
fig.suptitle("Ambient wind speed and direction")

# ## Convert to individual turbine histories
# Set turbine 0 history equal to delayed ambient (represents upstream turbine)
ws_0 = ws_u_inf[delay:]
wd_0 = wd_inf[delay:]

# Set turbine 1 and 2 histories with added noise (downstream turbines)
ws_1 = ws_u_inf[:N] + 0.25 * np.random.randn(N)
wd_1 = wd_inf[:N] + 1.0 * np.random.randn(N)
ws_2 = ws_u_inf[:N] + 0.5 * np.random.randn(N)
wd_2 = wd_inf[:N] + 2.5 * np.random.randn(N)

# Plot the separate turbine histories
fig, axarr = plt.subplots(2, 1, sharex=True)
axarr[0].plot(ws_0, color="k", label="Turbine 0")
axarr[0].plot(ws_1, color="r", label="Turbine 1", alpha=0.5)
axarr[0].plot(ws_2, color="b", label="Turbine 2", alpha=0.5)
axarr[0].set_ylabel("Wind speed [m/s]")
axarr[0].legend()
axarr[1].plot(wd_0, color="k", label="Turbine 0")
axarr[1].plot(wd_1, color="r", label="Turbine 1", alpha=0.5)
axarr[1].plot(wd_2, color="b", label="Turbine 2", alpha=0.5)
axarr[1].set_ylabel("Wind direction [deg]")
axarr[1].set_xlabel("Time step")

# ## Add histories to dataframe and save
# Note: For simplicity, set mean wind direction equal to turbine 0 direction
df = pd.DataFrame(
    {
        "time_utc": pd.date_range(start="1/1/2020", periods=N, freq="1s"),
        "wd_mean": wd_0,
        "ws_000": ws_0,
        "ws_001": ws_1,
        "ws_002": ws_2,
    }
)

fig.suptitle("Turbine wind speeds and directions")
df.to_feather("wind_input_small.ftr")

print(f"First time (UTC): {df['time_utc'].iloc[0]}")
print(f"Last time (UTC): {df['time_utc'].iloc[-1]}")

if show_plots:
    plt.show()
