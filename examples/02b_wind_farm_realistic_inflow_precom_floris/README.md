# Example 02b: Wind Farm Realistic Inflow (Precomputed FLORIS)

## Description

This example is identical to `02_wind_farm_realistic_inflow` with the exception that the `Wind_MesoToPowerPrecomFloris`
class is used to speed up the simulation. This example automatically generates the necessary input files in the centralized `examples/inputs/` folder when first run.

Note the caveats to using this class from the docs:


> In contrast to the Wind_MesoToPower class, this class pre-computes the FLORIS wake
    deficits for all possible wind speeds and power setpoints. This is done by running for
    all wind speeds and wind directions (but not over all power setpoints).  This is valid
    for cases where the wind farm is operating:
        - all turbines operating normally
        - all turbines off
        - following a wind-farm wide derating level

    It is in practice conservative with respect to the wake deficits, but it is more efficient
    than running FLORIS for each condition.  In cases where turbines are:
        - partially derated below the curtailment level
        - not uniformly curtailed or     some turbines are off

    This is not an appropriate model and the more general Wind_MesoToPower class should be used.




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