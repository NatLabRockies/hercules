# Solar PV

Hercules uses NREL [PySAM](https://nrel-pysam.readthedocs.io/en/main/overview.html) to drive NREL [System Advisor Model (SAM)](https://sam.nrel.gov) PV technology models.

The only solar implementation currently in Hercules is:

1. **`SolarPySAMPVWatts`** — [PVWatts](https://sam.nrel.gov/photovoltaic.html) via PySAM [`Pvwattsv8`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html). It is fast and suitable for long runs (e.g. about one year). Set `component_type: SolarPySAMPVWatts` in the component YAML. The section key is a user-chosen `component_name` (e.g. `solar_farm`); see [Component Names, Types, and Categories](component_types.md).



## Inputs

The solar component requires a weather time-series file. Supported formats are CSV, pickle (`.p`), Feather (`.f`/`.ftr`), and Parquet. The file should include:

- A `time_utc` column (see [timing](timing.md) for time format requirements). Each `time_utc` value marks the **start of a reporting period**; irradiance and weather on that row are period averages. See [Time Interpretation](timing.md#time-interpretation-inputs-vs-internal-values) for how Hercules converts them to instants.
- DNI, DHI, and GHI in columns whose names include the usual “Direct Normal…”, “Diffuse Horizontal…”, and “Global Horizontal…” substrings (see the solar module’s column lookup)
- Wind speed
- Air temperature (dry-bulb)


The system location (latitude, longitude, and elevation) is specified in the input `yaml` file.


## Outputs

At each time step, `h_dict[component_name]` is updated with:

- **`power`** (kW): **AC** plant power (PVWatts `Outputs.ac`, W → kW), then the AC setpoint is applied so this is the *delivered* AC when curtailment is active.
- **`dc_power_uncurtailed`** (kW): uncurtailed **pre-inverter** DC (PVWatts `Outputs.dc`, W → kW). It is not curtailed with the AC setpoint.

The YAML **`system_capacity`** is the **DC** array capacity at STC (kW), as in PVWatts. Inverter sizing and AC clipping follow PVWatts `SystemDesign` (including `dc_ac_ratio`); defaults can be changed under `pysam_options` (see below).

The PVWatts model is configured with the following default parameters for utility-scale installations:
- **Module type**: Standard crystalline silicon (module_type = 0)
- **Array type**: Single-axis tracking with backtracking (array_type = 3)
- **Azimuth**: 180° (due south)
- **DC/AC ratio**: 1.0

These parameters can be changed by using a `pysam_options` input dictionary in the yaml, shown below:
```yaml
solar_farm:
  component_type: SolarPySAMPVWatts
  system_capacity: 30000  # kW (30 MW)
  tilt: 0  # degrees
  losses: 0
  pysam_options:
    SystemDesign:
      array_type: 3.0  # single axis backtracking
      azimuth: 170.0
      dc_ac_ratio: 1.0  # kWac nameplate / kWdc STC; common default
      module_type: 0.0  # standard crystalline silicon
```
You can specify some or all of these parameters and the `pysam_options` parameters will always overwrite the defaults. These parameters represent the minimum parameters needed to define the solar model. For an exhaustive list of additional parameters you can set using this method, see [this page](https://h2integrate.readthedocs.io/en/stable/technology_models/pvwattsv8_solar_pv.html).

The array tilt angle must be specified in the input configuration file.

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.

**Available Channels:**
- `power`: AC plant power in kW (always logged; same quantity as in `h_dict` after the step)
- `dc_power_uncurtailed`: uncurtailed pre-inverter DC in kW (add to the list to include in the HDF5 output)
- `poa`: Plane-of-array irradiance in W/m²
- `dni`: Direct normal irradiance in W/m²
- `aoi`: Angle of incidence in degrees

**Example:**
```yaml
solar_farm:
  component_type: SolarPySAMPVWatts
  solar_input_filename: inputs/solar_input.csv
  log_channels:
    - power
    - dni
    - poa
    - aoi
  # ... other parameters
```

If `log_channels` is not specified, only `power` will be logged.

## Efficiency and loss parameters

PVWatts `SolarPySAMPVWatts` includes lumped and inverter-related terms; the ones exposed in typical Hercules YAML are:

- **`losses`**: system losses as a percentage (0–100). Affects the modeled **DC** side before the inverter in PVWatts. A common default is `0`.
- **`pysam_options` → `SystemDesign`**: e.g. `dc_ac_ratio`, `array_type`, `azimuth`, `module_type` (see PySAM / SAM documentation for the full set).

The `examples/03_wind_and_solar` case uses `SolarPySAMPVWatts` with a 30 MW DC STC `system_capacity`, `losses: 0`, and default single-axis backtracking. Location and weather are set in that example’s input YAML and resource files. Override `dc_ac_ratio` in `pysam_options` if you need a nameplate/clip point different from the default.


## References
PySAM (NREL). https://github.com/nrel/pysam
