# Output Files

Hercules generates HDF5 output files containing simulation data for analysis and visualization. This page describes the file format, available utilities for reading the data, and how the emulator generates these files.

## File Format

Hercules outputs simulation data in HDF5 (Hierarchical Data Format 5) format.  

## File Structure

The HDF5 file contains the following structure:

```
hercules_output.h5
├── data/
│   ├── time                    # Simulation time points (seconds)
│   ├── step                    # Simulation step numbers
│   ├── clock_time              # Wall clock time for each step
│   ├── time_utc                # UTC timestamps (if available)
│   ├── plant_power             # Total plant power output
│   ├── plant_locally_generated_power  # Locally generated power
│   ├── components/
│   │   ├── wind_farm.power     # Wind farm power output
│   │   ├── wind_farm.wind_speed # Wind speed at hub height
│   │   ├── solar_farm.power    # Solar farm power output
│   │   └── ...                 # Other component outputs
│   └── external_signals/
│       └── ...                 # Other external signals
└── metadata/
    ├── h_dict                  # Simulation configuration (JSON string)
    ├── start_time_utc          # Simulation start time (UTC timestamp)
    └── ...                     # Other metadata attributes
```

## Reading Output Files

Hercules provides several utilities in the `utilities` module for reading and analyzing output files:

### Basic Reading

```python
from hercules.utilities import read_hercules_hdf5

# Read entire file
df = read_hercules_hdf5("outputs/hercules_output.h5")
print(df.head())
```

### Subset Reading

For large datasets, you can read only specific columns or time ranges:

```python
from hercules.utilities import read_hercules_hdf5_subset

# Read specific columns
df_subset = read_hercules_hdf5_subset(
    "outputs/hercules_output.h5",
    columns=["wind_farm.power", "solar_farm.power", "external_signals.wind_speed"]
)

# Read specific time range (seconds)
df_time_range = read_hercules_hdf5_subset(
    "outputs/hercules_output.h5",
    time_range=(3600, 7200)  # 1-2 hours into simulation
)

# Combine both filters
df_filtered = read_hercules_hdf5_subset(
    "outputs/hercules_output.h5",
    columns=["plant.power"],
    time_range=(0, 3600)
)
```

### Metadata Access

```python
from hercules.utilities import get_hercules_metadata

# Get simulation metadata
metadata = get_hercules_metadata("outputs/hercules_output.h5")
print(f"Simulation configuration: {metadata['h_dict']}")
print(f"Start time: {metadata.get('start_time_utc')}")
```
