# Examples Overview

Hercules includes several example cases that demonstrate different simulation configurations and capabilities. All examples use a centralized input system where data files are automatically generated and stored in the `examples/inputs/` folder.

## Available Examples

- [00: Wind Farm Only](../examples/00_wind_farm_only/) - Simple wind farm simulation with generated wind data
- [01: Wind Farm DOF1 Model](../examples/01_wind_farm_dof1_model/) - 1-DOF long-duration wind simulation 
- [02: Wind Farm Realistic Inflow](../examples/02_wind_farm_realistic_inflow/) - Large-scale wind farm with longer running wind data
- [02b: Wind Farm Realistic Inflow (Precomputed FLORIS)](../examples/02b_wind_farm_realistic_inflow_precom_floris/) - Optimized version using precomputed wake deficits
- [03: Wind and Solar](../examples/03_wind_and_solar/) - Hybrid wind and solar plant with interconnect limits
- [04: Wind and Storage](../examples/04_wind_and_storage/) - Wind farm with battery storage system

## Input Data Management

All examples use centralized input files located in `examples/inputs/`:
- Wind data files (`.ftr` format)
- Solar data files (`.ftr` format) 
- FLORIS configuration files (`.yaml`)
- Turbine model files (`.yaml`)
- PV system configuration files (`.json`)

Input files are automatically generated when first running any example using the `ensure_example_inputs_exist()` function.

## Running Examples

Each example includes:
- `hercules_input.yaml`: Configuration file
- `hercules_runscript.py`: Main execution script
- `plot_outputs.py`: Output visualization script

To run any example:
```bash
cd examples/XX_example_name/
python hercules_runscript.py
```

No manual setup is required - all necessary input files will be automatically generated on first run.
