# Example 02c: Wind Farm Realistic Inflow (Direct - No Wake Modeling)

## Description

This example demonstrates the `Wind_MesoToPowerDirect` wake model, which assumes that wake effects are already included in the input wind data and performs no additional wake modeling. 

The `Wind_MesoToPowerDirect` component type uses `wake_model="none"` internally, which means:
- No FLORIS calculations are performed during the simulation (only at initialization to read turbine properties)
- `wind_speeds_withwakes` equals `wind_speeds_background` at all times
- Wake deficits are always zero
- Turbine dynamics (filter model or DOF1 model) still operate normally

This example automatically generates the necessary input files in the centralized `examples/inputs/` folder when first run.

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


