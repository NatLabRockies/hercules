# Script to download Grid Status data
# Documentation: https://nrel.github.io/hercules/gridstatus_download.html

# Note you will need an API key from Grid Status to use this script.

# To use this script in your project:
# 1. Copy this script into the folder where you want to download the data
# 2. Update the PARAMETERS section with your desired dataset, start date, end date, and filter
# 3. Run the script with an ephemeral environment via uvx like
#    uvx --with gridstatusio python grid_status_download.py

from gridstatusio import GridStatusClient

# PARAMETERS
QUERY_LIMIT = 20_000
dataset = "spp_lmp_real_time_5_min" 
start = "2024-01-01"
end = "2025-01-01"
filter_column = "location"
filter_value = "OKGE.FRONTIER"


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
columns_to_drop = ["interval_end_utc","location","location_type","pnode"]
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