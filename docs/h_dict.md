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
| **Plant Configuration** |
| `plant` | dict | Plant-level configuration | - |
| `plant.interconnect_limit` | float | Maximum power limit in kW | - |
| **Optional Global Parameters** |
| `verbose` | bool | Enable verbose logging | False |
| `name` | str | Simulation name | - |
| `description` | str | Simulation description | - |
| `output_file` | str | Output HDF5 file path | "outputs/hercules_output.h5" |
| `log_every_n` | int | Log every N simulation steps to output log (default: 1) | 1 |
| `external_data` | dict | External data configuration | - |
| `external_data_file` | str | External data file path (deprecated, use `external_data` instead) | - |
| `controller` | dict | Controller configuration | - |
| **Hybrid Plant Components** |

### Wind Farm (`wind_farm`)
| `component_type` | str | Must be "Wind_MesoToPower" or "Wind_MesoToPowerPrecomFloris" |
| `floris_input_file` | str | FLORIS input file path |
| `wind_input_filename` | str | Wind data input file |
| `turbine_file_name` | str | Turbine configuration file |
| `log_file_name` | str | Wind farm log file path |
| `log_channels` | list | List of channels to log (e.g., ["power", "wind_speed_mean_background", "turbine_powers"]) |
| `floris_update_time_s` | float | How often to update FLORIS wake calculations in seconds |

### Solar Farm (`solar_farm`)
| `component_type` | str | "SolarPySAMPVWatts" |
| **For SolarPySAMPVWatts:** |
| `pysam_model` | str | "pvwatts" |
| `solar_input_filename` | str | Solar data file path |
| `system_capacity` | float | DC system capacity in kW as defined by PVWatts - under Standard Test Conditions|
| `tilt` | float | Array tilt angle in degrees (required) |
| `lat` | float | Latitude |
| `lon` | float | Longitude |
| `elev` | float | Elevation in meters |
| `log_channels` | list | List of channels to log (e.g., ["power", "dni", "poa", "aoi"]) |
| `initial_conditions` | dict | Initial power, DNI, POA |

### Battery (`battery`)
| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `component_type` | str | "BatterySimple" or "BatteryLithiumIon" | Required |
| `energy_capacity` | float | Total capacity in kWh | Required |
| `charge_rate` | float | Maximum charge rate in kW | Required |
| `discharge_rate` | float | Maximum discharge rate in kW | Required |
| `max_SOC` | float | Maximum state of charge (0-1) | Required |
| `min_SOC` | float | Minimum state of charge (0-1) | Required |
| `initial_conditions` | dict | Contains initial SOC | Required |
| `allow_grid_power_consumption` | bool | Allow grid power consumption | False |
| `log_channels` | list | List of channels to log (e.g., ["power", "soc", "power_setpoint"]) | ["power"] |
| `roundtrip_efficiency` | float | Roundtrip efficiency (BatterySimple only) | 1.0 |
| `self_discharge_time_constant` | float | Self-discharge time constant in seconds (BatterySimple only) | inf |
| `track_usage` | bool | Enable usage tracking (BatterySimple only) | False |
| `usage_calc_interval` | int | Usage calculation interval in seconds (BatterySimple only) | 100 |
| `usage_lifetime` | float | Battery lifetime in years (BatterySimple only) | - |
| `usage_cycles` | int | Number of cycles until replacement (BatterySimple only) | - |

### Electrolyzer (`electrolyzer`)
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

### External Data (`external_data`)
| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `external_data_file` | str | Path to CSV file with external time series data | Optional (if not specified, `external_data` is ignored) |
| `log_channels` | list | List of channels to log to HDF5 output | None (log all) |

**Logging behavior:**
- `log_channels` **not specified**: All channels are logged (default)
- `log_channels: []` (empty list): No channels are logged
- `log_channels: [channel1, channel2]`: Only listed channels are logged

**Note**: All channels from the external data file are always available to the controller via `h_dict["external_signals"]`, regardless of the `log_channels` setting. The `log_channels` parameter only controls which channels are written to the HDF5 output file.

**Old format** (deprecated): Setting `external_data_file` at the top level is still supported but shows a deprecation warning. Use the `external_data` dict format instead.
