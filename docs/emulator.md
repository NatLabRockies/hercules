# Emulator

The `Emulator` class orchestrates the entire Hercules simulation, managing the main execution loop and coordinating between the controller, Python simulators, and output logging.

## Overview

The emulator serves as the central coordinator that drives the simulation forward step-by-step.

## Simulation Flow

For each time step:
1. Update external signals from interpolated data
2. Execute controller step (compute control actions)
3. Execute hybrid plant step (update component states)
4. Log current state to output file
5. Advance simulation time

