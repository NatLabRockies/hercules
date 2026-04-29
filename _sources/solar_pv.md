# Solar PV

Hercules uses NLR [PySAM](https://nrel-pysam.readthedocs.io/en/main/overview.html) to drive NLR [System Advisor Model (SAM)](https://sam.nlr.gov) PV technology models.

The only solar implementation currently in Hercules is:

1. **`SolarPySAMPVWatts`** — [PVWatts](https://sam.nlr.gov/photovoltaic.html) via PySAM [`Pvwattsv8`](https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html). It is fast and suitable for long runs (e.g. about one year). Set `component_type: SolarPySAMPVWatts` in the component YAML. The section key is a user-chosen `component_name` (e.g. `solar_farm`); see [Component Names, Types, and Categories](component_types.md).



## Inputs

The solar component requires a weather time-series file. Supported formats are CSV, pickle (`.p`), Feather (`.f`/`.ftr`), and Parquet. The file should include:

- A `time_utc` column (see [timing](timing.md) for time format requirements). Each `time_utc` value marks the **start of a reporting period**; irradiance and weather on that row are period averages. See [Time Interpretation](timing.md#time-interpretation-inputs-vs-internal-values) for how Hercules converts them to instants.
- DNI, DHI, and GHI in columns whose names include the usual “Direct Normal…”, “Diffuse Horizontal…”, and “Global Horizontal…” substrings (see the solar module’s column lookup)
- Wind speed
- Air temperature (dry-bulb)


The system location (latitude, longitude, and elevation) is specified in the input `yaml` file.


## Power Flow

The solar component models three distinct power quantities at each time step,
corresponding to successive stages along the plant's electrical path:

```{image} _static/solar_power_flow.svg
:alt: Solar power flow from arrays through inverters to the controller
:width: 700px
:align: center
```

- **`dc_power_available`** (kW): the full **DC potential** of the arrays, before
  the inverters. This is the modeled DC output (e.g. PVWatts `Outputs.dc`,
  W → kW) and reflects irradiance, temperature, and DC-side losses, but not
  inverter behavior or control.
- **`ac_power_available`** (kW): the **post-inverter AC potential** of the
  plant. It includes inverter inefficiency and AC clipping at the inverter
  nameplate (per PVWatts `Outputs.ac`, W → kW), but does not include any
  Hercules control-based curtailment.
- **`power`** (kW): the **delivered AC** power after the Hercules controller.
  When the controller imposes an AC setpoint below `ac_power_available`,
  `power` reflects the curtailed value; otherwise `power` equals
  `ac_power_available`.

## Outputs

At each time step, `h_dict[component_name]` is updated with `power`,
`ac_power_available`, and `dc_power_available` (all in kW), as well as the
weather/geometry diagnostics (`dni`, `poa`, `aoi`). All three power quantities
can be selected for HDF5 logging via `log_channels` (see below), though the `power` variable is always logged by default.

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
      dc_ac_ratio: 1.0
      module_type: 0.0  # standard crystalline silicon
```
You can specify some or all of these parameters and the `pysam_options` parameters will always overwrite the defaults. These parameters represent the minimum parameters needed to define the solar model. For an exhaustive list of additional parameters you can set using this method, see [this page](https://h2integrate.readthedocs.io/en/stable/technology_models/pvwattsv8_solar_pv.html).

The **`tilt`** is the array tilt angle in degrees, measured from horizontal, and must be specified in the input configuration file. Together with **`system_capacity`** and **`losses`** (see below), it is one of the three required top-level keys for the solar component; all other PVWatts parameters fall back to Hercules defaults or can be overridden under `pysam_options`.

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.

**Available Channels:**
- `power`: delivered AC plant power in kW after control (always logged; same quantity as in `h_dict` after the step)
- `ac_power_available`: post-inverter AC potential in kW, before control curtailment (add to the list to include in the HDF5 output)
- `dc_power_available`: pre-inverter DC potential of the arrays in kW (add to the list to include in the HDF5 output)
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

PVWatts `SolarPySAMPVWatts` includes lumped and inverter-related loss terms. The loss/efficiency parameters exposed in typical Hercules YAML are:

- **`losses`**: system losses as a percentage (0–100). Affects the modeled **DC** side before the inverter in PVWatts. A common default is `0`.
- **`pysam_options` → `SystemDesign`**: e.g. `dc_ac_ratio`, `array_type`, `azimuth`, `module_type` (see PySAM / SAM documentation for the full set).

The `examples/03_wind_and_solar` case uses `SolarPySAMPVWatts` with a 30 MW DC STC `system_capacity`, `losses: 0`, and default single-axis backtracking. Location and weather are set in that example’s input YAML and resource files. Override `dc_ac_ratio` in `pysam_options` if you need a nameplate/clip point different from the default.


## References
PySAM (NLR). https://github.com/NatLabRockies/pysam
