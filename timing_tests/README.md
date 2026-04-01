# Timing Tests

Utilities for benchmarking Hercules performance with standardized timing measurements.

## How It Works

The timing tests measure execution time of Hercules components and automatically record metadata (git commit, branch, CPU info, timestamp) to CSV files for tracking performance over time.

## Files

- `utilities.py` - Core `record_timing_result()` function for logging timing data
- `00_generate_wind_input.py` - Creates 50-turbine wind data for consistent testing
- `01_generate_solar_input.py` - Creates solar data for testing
- `02_plot_wind_solar_data.py` - Visualizes generated input data
- `03_run_wind_timing_test.py` - Benchmarks wind farm performance
- `04_run_solar_timing_test.py` - Benchmarks solar performance
- `hercules_input_wind.yaml` - Wind test configuration
- `hercules_input_solar.yaml` - Solar test configuration


## Running Tests

```bash
# Generate test data
python 00_generate_wind_input.py
python 01_generate_solar_input.py

# Plot the data
python 02_plot_wind_solar_data.py

# Run timing tests
python 03_run_wind_timing_test.py
python 04_run_solar_timing_test.py
```
