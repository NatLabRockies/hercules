# Emulator

The `Emulator` class orchestrates the entire Hercules simulation, managing the main execution loop and coordinating between the controller, Python simulators, and output logging.

## Overview

The emulator serves as the central coordinator that drives the simulation forward step-by-step, handling data logging, performance monitoring, and output file generation.

## Simulation Flow

For each time step:
1. Update external signals from interpolated data
2. Execute controller step (compute control actions)
3. Execute hybrid plant step (update component states)
4. Log current state to output file
5. Advance simulation time

## Configuration Options

### Logging Configuration

The emulator supports configurable logging frequency through the `log_every_n` parameter:

- **`log_every_n`** (int, optional): Controls how often simulation data is logged to the output file. 
  - Default: 1 (log every simulation step)
  - Example: `log_every_n: 5` logs data every 5 simulation steps
  - This reduces output file size and improves performance for long simulations

### Output File Generation

The emulator generates HDF5 output files containing comprehensive simulation data for analysis and visualization.

The output file includes metadata with:
- `dt_sim`: Simulation time step (seconds)
- `dt_log`: Logging time step (seconds) = `dt_sim * log_every_n`
- `log_every_n`: Logging stride value
- `start_clock_time` and `end_clock_time`: Wall clock timing information


For detailed information about the output file format and reading utilities, see the [Output Files](output_files.md) documentation.

