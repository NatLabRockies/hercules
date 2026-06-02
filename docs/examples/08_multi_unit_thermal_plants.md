# Example 08: Multi-unit Thermal Plants

## Description

This example demonstrates the operation of multiple thermal power plant units within a Hercules framework. The example showcases how different thermal generators (e.g., multiple OCGTs or combined cycle untis) can operate collectively to meet demand setpoints, including their coordinated startup and shutdown sequences, individual unit ramping constraints, and aggregate power output management. This builds upon Example 07 by illustrating how multiple thermal units with different characteristics can be simulated individually within a thermal plant.

For details on thermal component parameters and configuration, see {doc}`../open_cycle_gas_turbine`, {doc}`../steam_turbine`, {doc}`../combined_cycle_plant`, and {doc}`../thermal_plant`. For details on the underlying state machine and ramp behavior, see {doc}`../thermal_component_base`.

## Scenario

The simulation demonstrates multiple thermal units responding to changing power demand setpoints over a specified time horizon. Each unit independently manages its operational state (off, starting, on, stopping) and power output, subject to individual constraints. The controller coordinates the collective output of all units to track the demand profile. Key aspects that this functionality can be used for include:

- **Multi-unit coordination**: Units start and stop based on demand requirements and individual constraint timelines
- **Aggregate ramp rate limitations**: Combined ramp rates of multiple units can be managed for grid compliance
- **Minimum load considerations**: Multiple units provide flexibility to maintain system minimum load requirements
- **Economic dispatch**: Units may be prioritized based on efficiency characteristics (fuel consumption, heat rate)

### Key Behaviors Demonstrated

- **Parallel unit operation**: Multiple thermal units operate independently with their own state machines and constraints
- **Coordinated startup**: Units are brought online sequentially or in parallel based on demand and minimum down-time constraints
- **Demand following**: Collective output of all units tracks the requested power setpoint
- **Individual unit constraints**: Each unit respects its own minimum up/down times, ramp rates, and minimum stable loads
- **Shutdown sequencing**: Units are taken offline based on dispatch logic and minimum up-time satisfaction
- **Efficiency considerations**: Combined operation shows how multiple units can improve overall plant heat rate and fuel efficiency

## Setup

No manual setup is required. The example uses multiple thermal components (OCGTs and/or steam turbines) configured in the input file. Configuration details for each unit are specified in the YAML input file.

## Running

To run the example, execute the following command in the terminal:

```bash
python examples/08_multi_unit_thermal_plants/hercules_runscript.py

# OR

cd examples/08_multi_unit_thermal_plants
python hercules_runscript.py
```

## Outputs

The output files `hercules_output.h5` and `hercules_dict.echo` are written to the folder `examples/08_multi_unit_thermal_plants/outputs_08/` and log files are written to the folder `examples/08_multi_unit_thermal_plants/logger_outputs_08/`

To plot the outputs, run:

```bash
python examples/08_multi_unit_thermal_plants/plot_outputs.py
```

The plots show:
- Aggregate power output over time for all units combined
- Individual unit power output and state transitions
- Fuel consumption across all units
- Heat rate variation with load for the multi-unit plant
- Unit commitment status and startup/shutdown events
