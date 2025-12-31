# Grid Status Data Download

This page describes how to download LMP (Locational Marginal Pricing) data from [Grid Status](https://www.gridstatus.io/) for use in Hercules simulations.

## Basic Workflow

Refer to `examples/grid/grid_status_download_example.py` for an example of how to download LMP data from Grid Status. The script saves data in a lightly modified feather format that can be used directly in Hercules.

**If you need to combine real-time and day-ahead data for Hycon**, see the section on `generate_locational_marginal_price_dataframe_from_gridstatus()` at the end of this page.

## What is Grid Status?

[Grid Status](https://www.gridstatus.io/) is a platform that provides electricity market data including:
- Real-time and historical LMP data
- Market operations data
- Grid status information
- Power system reliability data

## API Key Setup

To use this script, you'll need an API key from Grid Status:

1. Visit [Grid Status API Settings](https://www.gridstatus.io/settings/api)
2. Sign up for an account if you don't have one
3. Generate an API key
4. Set the API key as an environment variable or configure it in your Grid Status client, this could done either by a shell command `export GRIDSTATUS_API_KEY=your_api_key` or by adding `export GRIDSTATUS_API_KEY="your_api_key"` to your `.bashrc` or `.zshrc` file

## Downloading LMP Data with `grid_status_download.py`

The `grid_status_download.py` example script downloads LMP data from Grid Status and saves it in a lightly modified feather format. The modifications are minimal:
- Removes columns not used by Hercules (`interval_end_utc`, `location`, `location_type`, `pnode`)
- Keeps the original time resolution and market type
- Saves as a feather file for efficient storage

The downloaded feather files can be used directly in Hercules for applications that need only real-time or only day-ahead data.

### Why uvx?

We recommend running the script with [uvx](https://docs.astral.sh/uv/guides/tools/) to run in an isolated environment because the `gridstatusio` package requires a different version of numpy than the rest of Hercules. Using uvx prevents dependency conflicts between the Grid Status client and Hercules' requirements.

See https://docs.astral.sh/uv/getting-started/installation/ for information in installing uv.

### Usage

To modify the example script to download data for your own use, you can:

1. Copy the script to your project folder
2. Update the parameters in the script:
   - `dataset`: Set to `"spp_lmp_real_time_5_min"` for real-time data, `"spp_lmp_day_ahead_hourly"` for day-ahead data, or any other Grid Status dataset
   - `start` and `end`: Date range for the data
   - `filter_column` and `filter_value`: These are used to select the node of interest
3. Run the script with uvx:
   ```bash
   uvx --with gridstatusio --with pyarrow python grid_status_download.py
   ```

If you need multiple datasets (e.g., both real-time and day-ahead), update the `dataset` parameter and run the script again.

See `examples/grid/grid_status_download_example.py` for an example that downloads both real-time and day-ahead datasets.

### Parameters

- **dataset**: The Grid Status dataset identifier (e.g., "spp_lmp_real_time_5_min", "spp_lmp_day_ahead_hourly"; see https://www.gridstatus.io/datasets for a complete list)
- **start**: Start date in YYYY-MM-DD format
- **end**: End date in YYYY-MM-DD format  
- **filter_column**: Column to filter on (usually "location" to select a node)
- **filter_value**: Value to filter by (should be the name of a node of interest, e.g., "OKGE.FRONTIER"; all nodes listed here: https://www.gridstatus.io/nodes)
- **QUERY_LIMIT**: Maximum number of rows to download (default: 20,000). Included to avoid accidentally using too much of account limit.

### Output

The script saves the downloaded data as a feather file (`.ftr`) with:
- Filename format: `gs_{dataset}_{start}_{filter_value}.ftr`
- Original time resolution (5-minute intervals for real-time, hourly for day-ahead)
- Original market type identifier preserved in the `market` column

## Combining Real-Time and Day-Ahead Data for Hycon

If you need to combine both real-time and day-ahead LMP data for use with Hycon, use the `generate_locational_marginal_price_dataframe_from_gridstatus()` function located in `hercules/grid/grid_utilities.py`.

**Note:** This step is only necessary if you need both real-time and day-ahead data combined. If you only need one type of data, you can use the feather files from `grid_status_download.py` directly.

The `generate_locational_marginal_price_dataframe_from_griddstatus()` function combines the real-time and day-ahead LMP data into a format optimized for Hycon:

- Merges real-time and day-ahead data at the base interval of the real-time data
- Creates hourly day-ahead LMP columns (`lmp_da_00` through `lmp_da_23`) for each hour of the day
- Forward-fills any missing values
- Generates "end" rows for each time interval for Hercules interpolation

See `examples/grid/process_grid_status_results.py` for a complete example.

### Output Format

The resulting DataFrame contains:
- `time_utc`: UTC timestamp
- ``: Real-time LMP at the base time interval
- `lmp_da`: Day-ahead LMP (forward-filled to the base interval)
- `lmp_da_00` through `lmp_da_23`: Day-ahead LMP for each hour of the day

This format is optimized for use with Hycon in Hercules simulations.
