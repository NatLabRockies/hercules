# Example 10: Long Run Wind Only

## Description

In this case use a first version of extracted data, rather then generated pseudo data.  The data is 
provided by Andrew Kumler and includes these notes:

> Wind data were extracted using the REsource eXtraction (rex) tool (https://nrel.github.io/rex/index.html).

> Each CSV file contains a yearly time seires of one variable from the WTK-LED. The index is 5-minutely with 100 points,
roughly creating a 10x10 box around the main point of interest (ARM SGP).

> The corresponding coordinates file (wtk-led_coords.csv) contains coordinates for each point (GID) that matches the
points in the variable files.

The original data is not committed to the repo so for this example to run must manually add the folder:

`example_case_folders/12_WindSimLongTerm_RealisticInflow/inputs/wind_resource_rex`

## Setup

Before running Hercules, the simulation is defined in `00_prepare_simulation.ipynb`.  This will create
the necessary input files for the simulation based on the originally provided data.


## Running

To run the example, execute the following command in the terminal:

```bash
bash run_script.sh
```
## Outputs

To plot the outputs run the following command in the terminal:

```bash
python plot_outputs.py
```