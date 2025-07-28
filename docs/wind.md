# Wind_MesoToPower

Wind_MesoToPower is a comprehensive wind farm simulator that focuses on meso-scale phenomena by applying a separate wind speed time signal to each turbine model derived from data. It combines FLORIS wake modeling with detailed turbine dynamics for long-term wind farm performance analysis.

## Overview

Wind_MesoToPower integrates FLORIS for wake effects with individual turbine models to simulate wind farm behavior over extended periods. It supports both simple filter-based turbine models and 1-degree-of-freedom (1-DOF) turbine dynamics.

## Configuration

Required parameters in [h_dict](h_dict.md):
- `floris_input_file`: FLORIS farm configuration
- `wind_input_filename`: Wind resource data file
- `turbine_file_name`: Turbine model configuration

Optional parameters:
- `floris_update_time_s`: FLORIS update interval (default: 60s)
- `floris_time_window_width_s`: Averaging window (default: 300s)
- `log_extra_outputs`: Enable detailed logging

## Turbine Models

### Filter Model
Simple first-order filter for power output smoothing with configurable time constants.

### 1-DOF Model
Advanced model with rotor dynamics, pitch control, and generator torque control.

## Outputs

- `power`: Total wind farm power
- `turbine_powers`: Individual turbine power outputs
- `turbine_deratings`: Current derating values
- `wind_speed`, `wind_direction`: Farm-level wind conditions
- Optional: FLORIS parameters, wake deficits, velocities 