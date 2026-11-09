# HerculesModel

The `HerculesModel` class orchestrates the entire Hercules simulation, managing the main execution loop and coordinating between the controller, HybridPlant, and output logging.

## Overview

The HerculesModel serves as the central coordinator that drives the simulation forward step-by-step, handling data logging, performance monitoring, and output file generation.

## Usage

HerculesModel is initialized with an input file, and then a controller is assigned separately. The simplest case is a pass-through controller:

```python
from hercules.hercules_model import HerculesModel

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")

# Define your controller class
class MyController:
    def __init__(self, h_dict):
        # Initialize with prepared h_dict
        pass

    def step(self, h_dict):
        # Implement control logic
        return h_dict

# Assign the controller to the model
hmodel.assign_controller(MyController(hmodel.h_dict))

# Run the simulation
hmodel.run()
```

The HerculesModel handles all initialization automatically:
- Sets up logging
- Loads and validates the input file
- Initializes the hybrid plant
- Adds plant metadata to h_dict

The controller is then assigned using the `assign_controller()` method, which:
- Takes a controller instance (not the class)
- The controller instance is initialized with the prepared h_dict from the model

## Simulation Flow

For each time step:
1. Update external signals from interpolated data
2. Execute controller step (compute control actions)
3. Execute hybrid plant step (update component states)
4. Log current state to output file
5. Advance simulation time

## Configuration Options

### Logging Configuration

HerculesModel logs every simulation step to the output file. This is a fixed assumption: the logging time step always equals the simulation time step `dt`.

### Output File Generation

The HerculesModel generates HDF5 output files containing comprehensive simulation data for analysis and visualization.

The output file includes metadata with:
- `dt_sim`: Simulation time step (seconds), which is also the output time step
- `start_clock_time` and `end_clock_time`: Wall clock timing information


For detailed information about the output file format and reading utilities, see the [Output Files](output_files.md) documentation.

## Logging Configuration

Hercules provides a unified `setup_logging()` function in the `hercules.utilities` module that handles all logging setup across the framework. This function is used internally by `HerculesModel` and all component classes, but can also be used directly for custom applications.

### Internal Usage

The `setup_logging()` function is called automatically by:
- `HerculesModel` during initialization (creates hercules logger)
- All component classes through `ComponentBase` (creates component-specific loggers)

Each component gets its own logger with an appropriate console prefix for easy identification of log messages.
