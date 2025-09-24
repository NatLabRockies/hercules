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
| `output_file` | str | Output CSV file path | "outputs/hercules_output.csv" |
| `time_log_interval` | int | Logging interval in steps | - |
| `log_every_n` | int | Log every N simulation steps (default: 1) | 1 |
| `external_data_file` | str | External data file path | - |
| `controller` | dict | Controller configuration | - |
| **Hybrid Plant Components** |

### Wind Farm (`wind_farm`)
| `component_type` | str | Must be "Wind_MesoToPower" |
| `floris_input_file` | str | FLORIS input file path |
| `wind_input_filename` | str | Wind data input file |
| `turbine_file_name` | str | Turbine configuration file |
| `log_file_name` | str | Wind farm log file path |
| `logging_option` | str | Logging level: "base", "turb_subset", or "all" |

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

