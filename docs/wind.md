# Wind Farm Components

## Wind_MesoToPower

Wind_MesoToPower is a comprehensive wind farm simulator that focuses on meso-scale phenomena by applying a separate wind speed time signal to each turbine model derived from data. It combines FLORIS wake modeling with detailed turbine dynamics for long-term wind farm performance analysis.

## Wind_MesoToPowerPrecomFloris

Wind_MesoToPowerPrecomFloris is an optimized variant of Wind_MesoToPower that pre-computes FLORIS wake deficits for improved simulation performance. This approach trades some accuracy for significant speed improvements in specific operating scenarios.

## Overview

Both wind farm components integrate FLORIS for wake effects with individual turbine models to simulate wind farm behavior over extended periods. They support both simple filter-based turbine models and 1-degree-of-freedom (1-DOF) turbine dynamics.

### Precomputed FLORIS Approach

Wind_MesoToPowerPrecomFloris pre-computes wake deficits for all wind speeds and directions at initialization, making it more efficient for long simulations. This approach is valid when the wind farm operates under these conditions:

- All turbines operating normally
- All turbines off 
- Following a wind-farm wide derating level

**Important**: This model is not appropriate when turbines are partially derated below the curtailment level or not uniformly curtailed. In such cases, use the standard Wind_MesoToPower class instead.

## Configuration

### Common Required Parameters

Required parameters for both components in [h_dict](h_dict.md):
- `floris_input_file`: FLORIS farm configuration
- `wind_input_filename`: Wind resource data file
- `turbine_file_name`: Turbine model configuration

### Wind_MesoToPower Specific Parameters

Required parameters for Wind_MesoToPower:
- `floris_update_time_s`: How often to update FLORIS (the last `floris_update_time_s` seconds are averaged as input)

Optional parameters for Wind_MesoToPower:
- `log_extra_outputs`: Enable detailed logging

### Wind_MesoToPowerPrecomFloris Specific Parameters

Optional parameters for Wind_MesoToPowerPrecomFloris:
- `log_extra_outputs`: Enable detailed logging

**Note**: `floris_update_time_s` is not used in the precomputed version since FLORIS is run only once during initialization.

## Turbine Models

### Filter Model
Simple first-order filter for power output smoothing with configurable time constants.

### 1-DOF Model
Advanced model with rotor dynamics, pitch control, and generator torque control.

## Outputs

### Common Outputs

Both components provide these outputs:
- `power`: Total wind farm power
- `turbine_powers`: Individual turbine power outputs  
- `turbine_power_setpoints`: Current power setpoint values
- `wind_speed`, `wind_direction`: Farm-level wind conditions

### Extra Outputs (when `log_extra_outputs: True`)

- `floris_wind_speed`: Wind speed used in FLORIS calculations
- `floris_wind_direction`: Wind direction used in FLORIS calculations
- `floris_ti`: Turbulence intensity values
- `unwaked_velocities`: Wind speeds without wake effects
- `waked_velocities`: Wind speeds with wake effects applied