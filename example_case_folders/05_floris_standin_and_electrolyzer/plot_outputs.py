# Plot the outputs of the simulation

import matplotlib.pyplot as plt
import pandas as pd

# Read the Hercules output file
df = pd.read_csv("hercules_output_control.csv", index_col=False)

# Plot the turbine powers
fig, ax = plt.subplots()
time = df["hercules_comms.amr_wind.wind_farm_0.sim_time_s_amr_wind"]
ax.plot(time, df["hercules_comms.amr_wind.wind_farm_0.turbine_powers.000"], label="WT000",lw=3)
ax.plot(time, df["hercules_comms.amr_wind.wind_farm_0.turbine_powers.001"], label="WT001")
ax.plot(time, df["py_sims.inputs.locally_generated_power"], label="Generated power")
ax.set_ylabel("Power [kW]")
ax.set_xlabel("Time")
ax.legend()
ax.grid()



fig, ax = plt.subplots()
ax.plot(time, df["py_sims.electrolyzer_stack_0.outputs.H2_output"], label="H2 Output")
ax.set_ylabel("H2 flowrate [kg/s]")
ax.set_xlabel("Time")
ax.legend()


print("Number of stacks operating:",df["py_sims.electrolyzer_stack_0.outputs.stacks_on"].iloc[-1])

plt.show()