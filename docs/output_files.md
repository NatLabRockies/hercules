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
    ├── dt_sim                  # Simulation time step (seconds)
    ├── dt_log                  # Logging time step (seconds)
    ├── log_every_n             # Logging stride value
    ├── start_clock_time        # Simulation start wall clock time
    ├── end_clock_time          # Simulation end wall clock time
    ├── start_time_utc          # Simulation start UTC time (if any component data contains time_utc)
    ├── zero_time_utc           # Simulation zero UTC time (if any component data contains time_utc)
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

### Convenience Class

For easier access to both data and metadata, you can use the `HerculesOutput` convenience class:

```python
from hercules import HerculesOutput

# Initialize with filename
ho = HerculesOutput("outputs/hercules_output.h5")

# Access metadata with dot notation
print(f"Simulation time step: {ho.dt_sim}")
print(f"Logging time step: {ho.dt_log}")
print(f"Simulation configuration: {ho.h_dict}")

# Access full data
data = ho.df
print(data.head())

# Get subset of data
subset = ho.get_subset(
    columns=["wind_farm.power", "solar_farm.power"],
    time_range=(3600, 7200)
)
```

The `HerculesOutput` class provides a convenient interface while still allowing direct access to the underlying utility functions if needed.

### Time UTC Reconstruction

If any component input data contains `time_utc` columns, the utilities can reconstruct UTC timestamps for each simulation step:

```python
from hercules.utilities import read_hercules_hdf5

# Read data with reconstructed time_utc
df = read_hercules_hdf5("outputs/hercules_output.h5")
if "time_utc" in df.columns:
    print(f"UTC timestamps available: {df['time_utc'].head()}")
```
