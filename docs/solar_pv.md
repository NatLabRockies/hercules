# Solar PV

The solar PV modules use the [PySAM](https://nrel-pysam.readthedocs.io/en/main/overview.html) package for the National Renewable Energy Laboratory's System Advisor Model (SAM) to predict the power output of the solar PV plant. 

Two different solar simulators are available, each implementing a different PySAM model:

1. **`SolarPySAMPVSam`** - Uses the [Detailed Photovoltaic model](https://sam.nrel.gov/photovoltaic.html) in [`Pvsamv1`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvsamv1.html), which calculates PV electrical output using separate module and inverter models. This model is more accurate, but more time-intensive. Set `component_type` = `SolarPySAMPVSam` in the input dictionary (.yaml file).

2. **`SolarPySAMPVWatts`** - Uses the [PVWatts model](https://sam.nrel.gov/photovoltaic.html) in [`Pvwattsv8`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html), which calculates estimated PV electrical output without detailed degradation or loss modeling. This model is less accurate, but less time-intensive, which makes it a good fit for longer duration simulations (of approximately 1 year). Set `component_type` = `SolarPySAMPVWatts` in the input dictionary (.yaml file).

### Inputs

Both models require an input weather file:
1. A CSV file that specifies the weather conditions (e.g. NonAnnualSimulation-sample_data-interpolated-daytime.csv). This file should include: 
    - timestamp
    - direct normal irradiance (DNI)
    - diffuse horizontal irradiance (DHI)
    - global horizontal irradiance (GHI)
    - wind speed
    - air temperature (dry bulb temperature)

The `SolarPySAMPVSam` model also requires an input system info file:

2. A JSON file that specifies the PV plant system design (e.g. 100MW_1axis_pvsamv1.json).

The system location (latitude, longitude, and elevation) is specified in the input `yaml` file.

The example folder `03_wind_and_solar` specifies:
- use of the `SolarPySAMPVWatts` model with `component_type: "SolarPySAMPVWatts"`
- weather conditions on May 10, 2018 measured at NREL's Flatirons Campus
- latitude, longitude, and elevation of Golden, CO
- system design information for a 100 MW single-axis PV tracking system (with backtracking)
The system capacity and AC/DC ratio inputs can be changed in the `.yaml` file.

For examples using the detailed `SolarPySAMPVSam` model, see the test files in the `tests/` directory.

### Outputs

Both solar modules output the AC power (`power`) in kW of the PV plant at each timestep. 

When `log_extra_outputs` is set to `True` in the input .yaml file, the solar modules also output plane-of-array irradiance (`poa`) in W/m^2, direct normal irradiance (`dni`) in W/m^2, and the angle of incidence (`aoi`) in degrees.

### References
PySAM. National Renewable Energy Laboratory. Golden, CO. https://github.com/nrel/pysam