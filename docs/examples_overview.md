# Examples Overview

Hercules includes several example cases that demonstrate different simulation configurations and capabilities. All examples use a centralized input system where data files are automatically generated and stored in the `examples/inputs/` folder.

## Available Examples

- [00: Wind Farm Only](../examples/00_wind_farm_only/) - Simple wind farm simulation with generated wind data
- [00b: Wind Farm SCADA Power](../examples/00b_wind_farm_scada_power) - Playback of pre-recorded SCADA turbine power data
- [01: Wind Farm DOF1 Model](../examples/01_wind_farm_dof1_model/) - 1-DOF long-duration wind simulation
- [02: Wind Farm Realistic Inflow](../examples/02_wind_farm_realistic_inflow/) - Large-scale wind farm with longer running wind data
- [02b: Wind Farm Realistic Inflow (Precomputed FLORIS)](../examples/02b_wind_farm_realistic_inflow_precom_floris/) - Optimized version using precomputed wake deficits
- [03: Wind and Solar](../examples/03_wind_and_solar/) - Hybrid wind and solar plant with interconnect limits
- [04: Wind and Storage](../examples/04_wind_and_storage/) - Wind farm with battery storage system
- [05: Wind and Storage with LMP](../examples/05_wind_and_storage_with_lmp/) - Battery control based on electricity pricing with selective external data logging
- [06: Wind and Hydrogen](../examples/06_wind_and_hydrogen/) - Wind farm with electrolyzer for hydrogen production

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

## Additional Resource Downloading and Upsampling Examples

Examples are provided in the `examples/inputs/` folder demonstrating how to download wind and solar data using the `hercules.resource.wind_solar_resource_downloader` module and upsample wind data using the `hercules.resource.upsample_wind_data` module to create inputs for Hercules simulations.

- [03: Download NSRDB and WIND Toolkit Solar and Wind Data](../examples/inputs/03_download_small_nsrdb_wtk_solar_wind_example.py) - Downloads a subset of solar and wind data for a small grid of locations for a single year from the NSRDB and WIND Toolkit datasets, respectively
- [04: Download and Upsample WIND Toolkit Wind Data](../examples/inputs/04_download_and_upsample_wtk_wind_example.py) - Downloads wind speed and direction for a small grid of locations for a single year from the WIND Toolkit dataset, then spatially interpolates the data at specific wind turbine locations and temporally upsamples the times series with added turbulence
- [05: Download Open-Meteo Solar and Wind Data](../examples/inputs/05_download_small_openmeteo_solar_wind_example.py) - Downloads a subset of solar and wind data for a small grid of locations for a single year using the Open-Meteo API
- [06: Download and Upsample Open-Meteo Wind Data](../examples/inputs/06_download_and_upsample_openmeteo_wind_example.py) - Downloads wind speed and direction for a small grid of locations for a single year using the Open-Meteo API, then spatially interpolates the data at specific wind turbine locations and temporally upsamples the times series with added turbulence
