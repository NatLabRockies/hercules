# Example 05: Wind and storage with LMP-based control

## Description

Example of a wind and storage hybrid plant with a controller that responds to Locational Marginal Pricing (LMP) signals. The controller:
- Charges the battery when real-time LMP is below $15/MWh (low prices)
- Discharges the battery when real-time LMP is above $35/MWh (high prices)
- Keeps the battery idle for intermediate prices

This example also demonstrates the new **selective external data logging** feature. Both `lmp_rt` and `lmp_da` are available to the controller via `h_dict["external_signals"]`, but only `lmp_rt` is logged to the HDF5 output file as specified in `log_channels`.

## Setup

No manual setup is required. The example automatically generates the necessary input files (wind data, FLORIS configuration, turbine model, and LMP data) when first run.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

The simulation runs for 4 hours with the following characteristics:
- Real-time LMP ramps from $0 to $50/MWh over 4 hours
- Day-ahead LMP remains constant at $10/MWh
- Only real-time LMP is logged to output (selective logging)

## Outputs

To plot the outputs, run the following command in the terminal:

```bash
python plot_outputs.py
```

The plot shows:
1. Wind and battery power with interconnect limits
2. Battery state of charge (SOC)
3. Battery power vs setpoint
4. LMP prices and control thresholds

Note that `lmp_rt` appears in the HDF5 output file, but `lmp_da` does not (as specified in `log_channels`), even though both were available to the controller.
