# Example version of the gridstatus_download.py script
# Download 2 days of data for the OKGE.FRONTIER location
# Download both real time and day ahead data
# See the documentation for more details of this example:
# https://nrel.github.io/hercules/gridstatus_download.html
# Note api key is required, see the documentation for more details:
# https://nrel.github.io/hercules/gridstatus_download.html#api-key-setup

# Run using uvx --with gridstatusio --with pyarrow python grid_status_download_example.py

from gridstatusio import GridStatusClient

# PARAMETERS
QUERY_LIMIT = 1000
start = "2024-01-01"
end = "2024-01-03"
filter_column = "location"
filter_value = "OKGE.FRONTIER"


for dataset in ["spp_lmp_real_time_5_min", "spp_lmp_day_ahead_hourly"]:
    # Initialize Grid Status client
    client = GridStatusClient()

    # Download data
    df = client.get_dataset(
        dataset=dataset,
        start=start,
        end=end,
        filter_column=filter_column,
        filter_value=filter_value,
        limit=QUERY_LIMIT,
    )

    print("--------------------------------")
    print(f"Downloaded {df.shape[0]} rows")

    # Print the first value of each column
    print("Columns:")
    for column in df.columns:
        print(f"{column}: {df[column].iloc[0]}")

    # Remove columns not used by hercules if in dataframe
    columns_to_drop = ["interval_end_utc", "location", "location_type", "pnode"]
    df = df.drop(columns=columns_to_drop, errors="ignore")

    # Show the dataframe head
    print("DataFrame head:")
    print(df.head())

    # Come up with a filename for the feather file
    filename = f"gs_{dataset}_{start}_{filter_value}"

    # Replace all dashes and dots with underscores
    filename = filename.replace("-", "_").replace(".", "_")

    # Add .ftr extension
    filename = filename + ".ftr"

    # Save the dataframe to a feather file
    df.to_feather(filename)

    print(f"Saved dataframe to {filename}")
