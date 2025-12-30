# Wind Farm Components

Hercules provides four wind farm simulation components that differ in their approach to wake modeling and data sources. The first three components support both simple filter-based turbine models and 1-degree-of-freedom (1-DOF) turbine dynamics, while the fourth component uses SCADA power data directly.


## Overview

The `WindFarm` component applies wind speed time signals to turbine models to simulate wind farm behavior over extended periods. This is available with different methods for how wakes are applies, as described below. The `WindFarmSCADAPower` component uses a fundamentally different approach by using actual SCADA power measurements as input.

## WindFarm (with Dynamic wake method)

`WindFarm` is a comprehensive wind farm simulator. When `wake_method="dynamic"` (the default), `WindFarm` computes wake effects dynamically at each time step (or at intervals specified by `floris_update_time_s`). It focuses on meso-scale phenomena by applying a separate wind speed time signal to each turbine model derived from data. This model combines FLORIS wake modeling with detailed turbine dynamics for long-term wind farm performance analysis.

**Use this model when:**
- Turbines have individual power setpoints or non-uniform operation
- Precise wake modeling is required for each control action
- Turbines may be partially derated or individually controlled

## WindFarm (with Precomputed wake method)

`WindFarm` with `wake_method="precomputed"` is an optimized variant that pre-computes all FLORIS wake deficits at initialization for improved simulation speed. This approach provides significant speed improvements while conservatively assuming wakes are always based on nominal operation.

**Use this model when:**
- Not investigating wakes of derated turbines or wake losses can be conservatively estimated.


## WindFarm (with No Added Wakes method)

Using `WindFarm` with `wake_method="no_added_wakes"` assumes that wake effects are already included in the input wind data and performs no wake modeling during simulation. This model is appropriate for using SCADA data of operational farm since wake losses already included in data.


## WindFarmSCADAPower (SCADA Power Data)

`WindFarmSCADAPower` uses SCADA power measurements directly rather than computing power from wind speeds and turbine models. This component applies a filter to the SCADA power data to simulate turbine response dynamics and respects power setpoint constraints.

_This model is a beta feature and is not yet fully tested._

## Configuration

### Common Required Parameters

Required parameters for both components in [h_dict](h_dict.md) (see [timing](timing.md) for time-related parameters):
- `floris_input_file`: FLORIS farm configuration
- `wind_input_filename`: Wind resource data file

### WindFarm Specific Parameters

Required parameters for WindFarm:
- `wake_method`: One of `"dynamic"`, `"precomputed"`, or `"no_added_wakes"` (defaults to `"dynamic"`)
- `floris_update_time_s`: How often to update FLORIS (the last `floris_update_time_s` seconds are averaged as input). Required for `"dynamic"` and `"precomputed"` wake methods; for `"no_added_wakes"`, this parameter is not required and ignored if provided.
- `turbine_file_name`: Turbine model configuration
- `log_channels`: List of output channels to log. See [Logging Configuration](wind-logging-configuration) section below for details.

### WindFarmSCADAPower Specific Parameters

Required parameters for WindFarmSCADAPower:
- `scada_filename`: Path to SCADA data file (CSV, pickle, or feather format)
- `turbine_file_name`: Turbine model configuration (for filter parameters)
- `log_channels`: List of output channels to log. See [Logging Configuration](#logging-configuration) section below for details.

**SCADA File Format:**

The SCADA file must contain the following columns:
- `time_utc`: Timestamps in UTC (ISO 8601 format or parseable datetime strings)
- `wd_mean`: Mean wind direction in degrees
- `pow_###`: Power output for each turbine (e.g., `pow_000`, `pow_001`, `pow_002`)

Optional columns:
- `ws_###`: Wind speed for each turbine (e.g., `ws_000`, `ws_001`, `ws_002`)
- `ws_mean`: Mean wind speed (used if individual turbine speeds not provided)
- `ti_###`: Turbulence intensity for each turbine (defaults to 0.08 if not provided)

The number of turbines and rated power are automatically inferred from the SCADA data.

## Turbine Models

**Note:** WindFarmSCADAPower does not use a filter model as power values come directly from SCADA data rather than being computed from wind speedes.

### Filter Model
Simple first-order filter for power output smoothing with configurable time constants.

### 1-DOF Model
Advanced model with rotor dynamics, pitch control, and generator torque control. Not applicable to WindFarmSCADAPower.

## Outputs

### Common Outputs

All four components provide these outputs in the h_dict at each simulation step:
- `power`: Total wind farm power (kW)
- `turbine_powers`: Individual turbine power outputs (array, kW)
- `turbine_power_setpoints`: Current power setpoint values (array, kW)
- `wind_speed_mean_background`: Farm-average background wind speed (m/s)
- `wind_speed_mean_withwakes`: Farm-average with-wakes wind speed (m/s)
- `wind_direction_mean`: Farm-average wind direction (degrees)
- `wind_speeds_background`: Per-turbine background wind speeds (array, m/s)
- `wind_speeds_withwakes`: Per-turbine with-wakes wind speeds (array, m/s)


**Note for WindFarm with no_added_wakes and WindFarmSCADAPower:** In these models (no wake modeling), `wind_speeds_withwakes` equals `wind_speeds_background` and `wind_speed_mean_withwakes` equals `wind_speed_mean_background`.

(wind-logging-configuration)=
## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.

### Available Channels

**Scalar Channels:**
- `power`: Total wind farm power output (kW)
- `wind_speed_mean_background`: Farm-average background wind speed (m/s)
- `wind_speed_mean_withwakes`: Farm-average with-wakes wind speed (m/s)  
- `wind_direction_mean`: Farm-average wind direction (degrees)

**Array Channels:**
- `turbine_powers`: Power output for all turbines (creates datasets like `wind_farm.turbine_powers.000`, `wind_farm.turbine_powers.001`, etc.)
- `turbine_power_setpoints`: Power setpoints for all turbines
- `wind_speeds_background`: Background wind speeds for all turbines
- `wind_speeds_withwakes`: With-wakes wind speeds for all turbines

### Selective Array Element Logging

For large wind farms, logging all turbine data can significantly increase file size and slow down the simulation. You can log specific turbine indices by appending a 3-digit turbine index to the channel name:

```yaml
# Log only turbines 0, 5, and 10
log_channels:
  - power
  - wind_speed_mean_background
  - wind_speed_mean_withwakes
  - wind_direction_mean
  - turbine_powers.000
  - turbine_powers.005
  - turbine_powers.010
```

### Example Configurations

**Minimal Logging:**
```yaml
log_channels:
  - power
  - wind_speed_mean_background
  - wind_speed_mean_withwakes
  - wind_direction_mean
```

**Detailed Logging (all turbines):**
```yaml
log_channels:
  - power
  - wind_speed_mean_background
  - wind_speed_mean_withwakes
  - wind_direction_mean
  - turbine_powers
  - wind_speeds_withwakes
```

**Selected Turbine Logging:**
```yaml
# Log first 3 turbines only
log_channels:
  - power
  - wind_speed_mean_background
  - wind_speed_mean_withwakes
  - wind_direction_mean
  - turbine_powers.000
  - turbine_powers.001
  - turbine_powers.002
```