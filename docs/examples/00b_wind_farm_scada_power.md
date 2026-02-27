# Example 00b: Wind Farm SCADA Power

## Description

This example demonstrates the use of `WindFarmSCADAPower` to simulate a wind farm using pre-recorded SCADA power data. `WindFarmSCADAPower` is primarily useful when the actual turbine powers are provided and we want to play back the pre-recorded power data. There is no option to control the turbine powers; they are simply played back at the pre-recorded power levels.

## Setup

As in example 00, the wind farm is a small 3 turbine farm and the input is automatically generated. For `WindFarmSCADAPower` this input is a history of pre-recorded turbine power data in `inputs/scada_input.ftr`.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

## Outputs

To plot the outputs, run the following command in the terminal:

```bash
python plot_outputs.py
```
