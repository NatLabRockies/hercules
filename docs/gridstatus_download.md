# Grid Status Data Download

This script downloads LMP (Locational Marginal Pricing) data from [Grid Status](https://www.gridstatus.io/) for use in Hercules simulations. Grid Status provides comprehensive electricity market data including real-time and historical pricing information.

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
4. Set the API key as an environment variable or configure it in your Grid Status client

## Why uvx?

This script uses [uvx](https://docs.astral.sh/uv/guides/tools/) to run in an isolated environment because the `gridstatusio` package requires a different version of numpy than the rest of Hercules. Using uvx prevents dependency conflicts between the Grid Status client and Hercules' requirements.

## Usage

1. Copy the script to your project folder
2. Update the parameters in the script:
   - `dataset`: The Grid Status dataset to download (e.g., "spp_lmp_real_time_5_min")
   - `start` and `end`: Date range for the data
   - `filter_column` and `filter_value`: These are used to select the node of interest
3. Run the script with uvx:
   ```bash
   uvx --with gridstatusio --with pyarrow python grid_status_download.py
   ```

## Parameters

- **dataset**: The Grid Status dataset identifier (e.g., "spp_lmp_real_time_5_min")
- **start**: Start date in YYYY-MM-DD format
- **end**: End date in YYYY-MM-DD format  
- **filter_column**: Column to filter on (usually "location" to select a node)
- **filter_value**: Value to filter by (should be the name of a node of interest, eg "OKGE.FRONTIER")
- **QUERY_LIMIT**: Maximum number of rows to download (default: 20,000.)  Included to avoid accidentally using too much of account limit.

## Output

The script saves the downloaded data as a feather file (`.ftr`) with:
- Cleaned column names (removes columns unused by Hercules)
- Renamed time column to `time_utc`
- Filename format: `gs_{dataset}_{start}_{filter_value}.ftr`

The feather file can be used now to provide LMP information to Hercules runs.
