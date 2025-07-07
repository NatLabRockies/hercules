# Example 13: Long Run Wind and Solar

## Description

This example uses the Python simulator for wind power output and PySAM's PVWatts model for solar power output. This example was developed to run Hercules for long durations (up to 1 year).

The input solar resource data is a subset of the Flatirons irradiance data at sunset, to capture varying power output from the solar farm.


## Running

Before running the example generate the solar input by running resample_solar_history.ipynb

To run the example, execute the following command in the terminal:

```bash
bash run_script.sh
```
## Outputs

To plot the outputs run the following command in the terminal:

```bash
python plot_outputs.py
```