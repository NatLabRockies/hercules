# Order of Operations

## Initialization

1. Load configuration from YAML input file into `h_dict`
2. Initialize controller
3. Initialize hybrid plant components based on `h_dict` configuration
4. Initialize emulator with controller, hybrid plant, and configuration
5. Add plant component metadata to `h_dict`
6. Load external data files if specified

## Main Simulation Loop

For each time step:

1. **Update external signals** from interpolated data (if external data file provided)
2. **Execute controller step** - compute control actions based on current state
3. **Execute hybrid plant step** - update all component states and compute outputs
4. **Compute plant-level outputs** - aggregate individual component results
5. **Log current state** to output file
6. **Advance simulation time** and repeat until end time reached

## Component Execution Order

Within each hybrid plant step:
- All components execute their `step()` method in parallel
- Each component updates its internal state and outputs
- Plant-level power is computed as sum of all component powers
- Locally generated power is computed as sum of generator component powers (excluding storage/electrolyzer)

