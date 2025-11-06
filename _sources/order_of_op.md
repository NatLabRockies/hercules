# Order of Operations

## Initialization

1. Initialize HerculesModel with YAML input file
2. Load and validate configuration into `h_dict`
3. Initialize hybrid plant components based on `h_dict` configuration
4. Add plant component metadata to `h_dict`
5. Load external data files if specified
6. Initialize controller instance with the prepared `h_dict`
7. Assign controller to HerculesModel using `assign_controller()` method

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

