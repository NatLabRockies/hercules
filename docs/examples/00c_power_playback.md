# Example 00c: Power Playback

## Description

This example demonstrates the use of `PowerPlayback` to replay pre-recorded power data as
a generic power-generating unit in a Hercules simulation. `PowerPlayback` is useful when
measured or externally modeled power output is available and no physics model is needed —
the power values are simply played back at each time step with no control interface.

The simulation runs for approximately 15 minutes and 50 seconds, playing back a step-function
power profile: zero output for the first half, then rated output for the second half.

## Setup

No manual setup is required. The example automatically generates the necessary input file
(`power_playback_input.ftr`) in the centralized `examples/inputs/` folder when first run.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

## Outputs

To plot the outputs, run the following command in the terminal:

```bash
python plot_outputs.py
```
