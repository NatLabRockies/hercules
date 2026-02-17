# Example 02b: Wind Farm Realistic Inflow (Precomputed FLORIS)

## Description

This example is identical to `02a_wind_farm_realistic_inflow` with the exception that the `precomputed` wake method is used to speed up the simulation. The configuration sets `wake_method: precomputed` in the `wind_farm` component. This example automatically generates the necessary input files in the centralized `examples/inputs/` folder when first run.

Note the caveats to using this method from the docs:


> In contrast to `wake_method: dynamic`, this method pre-computes the FLORIS wake
    deficits for all possible wind speeds and power setpoints. This is done by running for
    all wind speeds and wind directions (but not over all power setpoints).  This is valid
    for cases where the wind farm is operating in the following ways:
        - all turbines operating normally (maximum power)
        - all turbines off
        - following a wind-farm wide derating level

    It is in practice conservative with respect to the wake deficits, but it is more efficient
    than running FLORIS for each condition at each time step.  In cases where turbines are:
        - partially derated below the curtailment level
        - some, but not all, turbines are off
    this is not an appropriate model and the more general `wake_method: dynamic` should be used.

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
