# H_Dict Structure

The `h_dict` (Hercules Dictionary) is the central configuration structure used throughout the Hercules simulation framework. It contains all simulation parameters, component configurations, and runtime state information.  It is a nested dictionary with defined components.

## Structure Overview

The `h_dict` is a Python dictionary that contains all the configurations for each plant component. The structure is designed to be flexible, allowing users to include only the components they need for their specific simulation scenario.

## Complete H_Dict Structure

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| **Simulation Parameters** |
| `dt` | float | Time step size in seconds | - |
| `starttime` | float | Simulation start time in seconds | - |
| `endtime` | float | Simulation end time in seconds | - |
| `step` | int | Current simulation step | 0 |
| `time` | float | Current simulation time | starttime |
| **Output File Configuration** |
| `output_dir` | str | Output folder name | "outputs" |
| `output_filename` | str | Output HDF5 file name | "hercules_output.h5" |
| `auto_increment_filenames` | bool | If True, append an incrementing number to an existing output filename instead of replacing it | False |
| **Logging Configuration** |
| `logging` | dict | Logging configuration | - |
| `logging.logger_name` | str | Name of logger | "hercules" |
| `logging.logger_file` | dict | Log file name | "log_hercules.log" |
| `logging.console_output` | bool | Whether to log to console | True |
| `logging.console_prefix` | str | Logger prefix | "HERCULES" |
| `logging.log_level` | str | Logging level | "INFO" |
| `logging.logging_dir` | str | Logger output dir | "outputs" |
| **Plant Configuration** |
| `plant` | dict | Plant-level configuration | - |
| `plant.interconnect_limit` | float | Maximum power limit in kW | - |
| `plant.efficiency_bus_to_poi` | float | One-way LV bus to POI efficiency, in (0, 1] | 1.0 |
| **Optional Global Parameters** |
| `verbose` | bool | Enable verbose logging | False |
| `name` | str | Simulation name | - |
| `description` | str | Simulation description | - |
| `external_data` | dict | External data configuration | - |
| `controller` | dict | Controller configuration | - |
| **Hybrid Plant Components** |

Any top-level `h_dict` entry whose value is a dict containing a `component_type` key is auto-discovered as a plant component. The key is a user-chosen `component_name` (e.g. `wind_farm`, `battery_unit_1`) — it does not need to match the category name. See [Component Names, Types, and Categories](component_types.md) for details.

### Wind Farm
| `component_type` | str | Must be "WindFarm" or "WindFarmSCADAPower" |
| `floris_input_filename` | str | FLORIS input file path |
| `wind_input_filename` | str | Wind data input file |
| `turbine_filename` | str | Turbine configuration file |
| `log_filename` | str | Wind farm log file path |
| `log_channels` | list | List of channels to log (e.g., ["power", "power_hypothetical", "wind_speed_mean_background", "turbine_powers"]) |
| `floris_update_time` | float | How often to update FLORIS wake calculations in seconds |

### Solar Farm
| `component_type` | str | "SolarPySAMPVWatts" |
| **For SolarPySAMPVWatts:** |
| `solar_input_filename` | str | Solar data file path |
| `system_capacity` | float | DC system capacity in kW (PVWatts STC) |
| `tilt` | float | Array tilt angle in degrees (required) |
| `losses` | float | System losses, % (0–100); see [Solar PV](solar_pv.md) |
| `pysam_options` | dict | Optional; e.g. `SystemDesign: {dc_ac_ratio, array_type, ...}` — see [Solar PV](solar_pv.md) |
| `use_resource_solar_dt` | bool | Optional; default `true`. If the weather file's resource dt is coarser than `dt`, run PySAM once at resource resolution and upsample its outputs to the Hercules grid — see [Solar PV](solar_pv.md#resource-resolution-pysam-execution-use_resource_solar_dt) |
| `lat` | float | Latitude |
| `lon` | float | Longitude |
| `elev` | float | Elevation in meters |
| `log_channels` | list | Channels to log (e.g. `power`, `power_hypothetical`, `DC_power_hypothetical`, `DNI`, `POA`, `AOI`) — see [Solar PV](solar_pv.md) |
| `initial_conditions` | dict | Initial `power`, `DNI`, `POA` placeholders; modeled values are not all applied on init, and `power` is updated to the modeled AC value on the first `step()` |

### Battery
| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `component_type` | str | "BatteryDynamic", "BatteryReservoir" or "BatteryLithiumIon" | Required |
| `energy_capacity` | float | Deliverable energy capacity in kWh | Required |
| `power_charge_max` | float | Maximum charge rate in kW | Required |
| `power_discharge_max` | float | Maximum discharge rate in kW | Required |
| `SOC_max` | float | Maximum state of charge (0-1). Values < 1 indicate degradation. | 1.0 |
| `SOC_min` | float | Minimum state of charge (0-1). Values > 0 indicate degradation. | 0.0 |
| `initial_conditions` | dict | Contains initial SOC | Required |
| `allow_grid_power_consumption` | bool | Allow grid power consumption | False |
| `log_channels` | list | List of channels to log (e.g., ["power", "DC_power", "SOC", "power_setpoint"]) | ["power"] |
| `roundtrip_efficiency` | float | Roundtrip efficiency (0-1), applied on charging (BatteryDynamic and BatteryReservoir) | 1.0 |
| `time_constant_self_discharge` | float | Self-discharge time constant in seconds (BatteryDynamic and BatteryReservoir) | inf |

### Electrolyzer
| Key | Type | Description |
|-----|------|-------------|
| `initialize` | bool | Initialize electrolyzer |
| `initial_power_kW` | float | Initial power in kW |
| `supervisor` | dict | Supervisor configuration |
| `stack` | dict | Stack configuration |
| `controller` | dict | Controller configuration |
| `costs` | dict | Cost parameters |
| `cell_params` | dict | Cell parameters |
| `degradation` | dict | Degradation parameters |

### Open Cycle Gas Turbine

Set `component_type: OpenCycleGasTurbine`. See {doc}`open_cycle_gas_turbine` for the full parameter reference.

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `component_type` | str | `"OpenCycleGasTurbine"` | Required |
| `capacity_rated` | float | Rated power output in kW | Required |
| `initial_conditions` | dict | Initial state (`power`, `state`) | Required |
| `load_stable_min_fraction` | float | Minimum stable load as fraction of rated capacity | 0.40 |
| `ramp_rate_fraction_per_min` | float | Ramp rate as fraction of rated capacity per minute | 0.10 |
| `log_channels` | list | List of channels to log | `["power"]` |

### External Data (`external_data`)
| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `external_data_filename` | str | Path to CSV file with external time series data | Optional (if not specified, `external_data` is ignored) |
| `log_channels` | list | List of channels to log to HDF5 output | None (log all) |

**Logging behavior:**
- `log_channels` **not specified**: All channels are logged (default)
- `log_channels: []` (empty list): No channels are logged
- `log_channels: [channel1, channel2]`: Only listed channels are logged

**Note**: All channels from the external data file are always available to the controller via `h_dict["external_signals"]`, regardless of the `log_channels` setting. The `log_channels` parameter only controls which channels are written to the HDF5 output file.
