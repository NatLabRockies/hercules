# Wind Farm Components

## Wind_MesoToPower

Wind_MesoToPower is a comprehensive wind farm simulator that focuses on meso-scale phenomena by applying a separate wind speed time signal to each turbine model derived from data. It combines FLORIS wake modeling with detailed turbine dynamics for long-term wind farm performance analysis.

## Wind_MesoToPowerPrecomFloris

Wind_MesoToPowerPrecomFloris is an optimized variant of Wind_MesoToPower that pre-computes FLORIS wake deficits for improved simulation performance. This approach trades some accuracy for significant speed improvements in specific operating scenarios.

## Overview

Both wind farm components integrate FLORIS for wake effects with individual turbine models to simulate wind farm behavior over extended periods. They support both simple filter-based turbine models and 1-degree-of-freedom (1-DOF) turbine dynamics.

### Precomputed FLORIS Approach

Wind_MesoToPowerPrecomFloris pre-computes wake deficits using a fixed cadence determined by `floris_update_time_s`. At initialization, FLORIS is evaluated at that cadence using right-aligned time-window averages of wind speed, wind direction, and turbulence intensity. The resulting wake deficits are then held constant between evaluations and applied to the per-turbine inflow time series.

This approach is valid when the wind farm operates under these conditions:

- All turbines operating normally
- All turbines off 
- Following a wind-farm wide derating level

Important: This model is not appropriate when turbines are partially derated below the curtailment level or not uniformly curtailed. In such cases, use the standard Wind_MesoToPower class instead.

## Configuration

### Common Required Parameters

Required parameters for both components in [h_dict](h_dict.md) (see [timing](timing.md) for time-related parameters):
- `floris_input_file`: FLORIS farm configuration
- `wind_input_filename`: Wind resource data file
- `turbine_file_name`: Turbine model configuration

### Wind_MesoToPower Specific Parameters

Required parameters for Wind_MesoToPower:
- `floris_update_time_s`: How often to update FLORIS (the last `floris_update_time_s` seconds are averaged as input)
- `log_channels`: List of output channels to log. See [Logging Configuration](wind-logging-configuration) section below for details.

### Wind_MesoToPowerPrecomFloris Specific Parameters

Required parameters for Wind_MesoToPowerPrecomFloris:
- `floris_update_time_s`: Determines the cadence of wake precomputation. At each cadence tick, the last `floris_update_time_s` seconds are averaged and used to evaluate FLORIS. The computed wake deficits are then applied until the next cadence tick.
- `log_channels`: List of output channels to log. See [Logging Configuration](wind-logging-configuration) section below for details.

## Turbine Models

### Filter Model
Simple first-order filter for power output smoothing with configurable time constants.

### 1-DOF Model
Advanced model with rotor dynamics, pitch control, and generator torque control.

## Outputs

### Common Outputs

Both components provide these outputs in the h_dict at each simulation step:
- `power`: Total wind farm power (kW)
- `turbine_powers`: Individual turbine power outputs (array, kW)
- `turbine_power_setpoints`: Current power setpoint values (array, kW)
- `wind_speed_mean_background`: Farm-average background wind speed (m/s)
- `wind_speed_mean_withwakes`: Farm-average with-wakes wind speed (m/s)
- `wind_direction_mean`: Farm-average wind direction (degrees)
- `wind_speeds_background`: Per-turbine background wind speeds (array, m/s)
- `wind_speeds_withwakes`: Per-turbine with-wakes wind speeds (array, m/s)

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