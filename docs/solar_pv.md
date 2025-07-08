# Solar PV

The `SolarPySAM` module uses [PySAM](https://nrel-pysam.readthedocs.io/en/main/overview.html) package for the National Renewable Energy Laboratory's System Advisor Model (SAM) to predict the power output of the solar PV plant. 

To calculate PV electrical output, the user specifices which specific model is used:
1. The [Detailed Photovoltaic model](https://sam.nrel.gov/photovoltaic.html) in [`Pvsamv1`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvsamv1.html), which calculates PV electrical output using separate module and inverter models. This model is more accurate, but more time-intensive. This model is set by using `pysam_model` = `pvsam` in the input dictionary.
2. The [PVWatts model](https://sam.nrel.gov/photovoltaic.html) in [`Pvwattsv8`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html), which calculates estimated PV electrical output without detailed degradation or loss modeling. This model is less accurate, but less time-intensive, which makes it a good fit for longer duration simulations (of approximately 1 year). This model is set by using `pysam_model` = `pvwatts` in the input dictionary.

### Inputs

Both the `Pvsamv1` and `Pvwattsv8` models require an input weather file:
1. A CSV file that specifies the weather conditions (e.g. NonAnnualSimulation-sample_data-interpolated-daytime.csv). This file should include: 
    - timestamp
    - direct normal irradiance (DNI)
    - diffuse horizontal irradiance (DHI)
    - global horizontal irradiance (GHI)
    - wind speed
    - air temperature (dry bulb temperature)

The `Pvsamv1` model also requires an input system info file:
2.  A JSON file that specifies the PV plant system design (e.g. 100MW_1axis_pvsamv1.json).
The system location (latitude, longitude, and elevation) is specified in the input `yaml` file.

The example folder `07_floris_standin_and_solar_pysam` specifies:
- use of the `Pvsamv1` model with the input `pvsam`
- weather conditions on May 10, 2018 measured at NREL's Flatirons Campus
- latitude, longitude, and elevation of Golden, CO
- system design information for a 130 MW single-axis PV tracking system (with backtracking)
These inputs can be changed in the `.yaml` and `.csv` files.

The example folder `13_WindSolarSimLongTerm` specifies:
- use of the `Pvwattsv8` model with the input `pvwatts`
- weather conditions on May 10, 2018 measured at NREL's Flatirons Campus
- latitude, longitude, and elevation of Golden, CO
- system design information for a 100 MW single-axis PV tracking system (with backtracking)

### Outputs

The `SolarPySAM` module outputs the AC power (`power`) and the net DC power (`dc_power`) in kW of the PV plant at each timestep, as well as the angle of incidence (`aoi`).

### References
PySAM. National Renewable Energy Laboratory. Golden, CO. https://github.com/nrel/pysam