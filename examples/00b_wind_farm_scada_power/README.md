# Example 00b: Wind farm SCADA power

## Description

Demonstrate the use of `WindFarmSCADAPower` to simulate a wind farm using SCADA power data.  `WindFarmSCADAPower` is useful when the input available is not wind speeds but rather SCADA power data.

## Setup

As in example 00, the wind farm is a small 3 turbine farm and the input is automatically generated.  For `WindFarmSCADAPower` this input is a history of pre-recorded turbine power data in `inputs/scada_input.ftr`.

  Also as in example 00, turbine 0's power is toggled every 100 seconds.  This means the will sometimes follow the pre-recorded power data and sometimes be curtailed below it.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

## Outputs

To plot the outputs run the following command in the terminal:

```bash
python plot_outputs.py
```