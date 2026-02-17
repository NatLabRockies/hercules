# Process the results of the grid status download
# using generate_locational_marginal_price_dataframe.
# The output dataframe is formatted for use as external data in Hercules and includes convenient
# forward hours of day ahead for certain Hycon applications.
# See the documentation for more details of this example:
# https://natlabrockies.github.io/hercules/gridstatus_download.html#combining-real-time-and-day-ahead-data-for-hycon

import pandas as pd
from hercules.grid.grid_utilities import (
    generate_locational_marginal_price_dataframe_from_gridstatus,
)

# Read the real time and day ahead data
df_rt = pd.read_feather("gs_spp_lmp_real_time_5_min_2024_01_01_OKGE_FRONTIER.ftr")
df_da = pd.read_feather("gs_spp_lmp_day_ahead_hourly_2024_01_01_OKGE_FRONTIER.ftr")

# Print the first 10 rows of each dataframe
print("First 10 rows of real time data:")
print(df_rt.head(10))
print("First 10 rows of day ahead data:")
print(df_da.head(10))
print("--------------------------------")

# Process the data
df = generate_locational_marginal_price_dataframe_from_gridstatus(
    df_da,
    df_rt,
    day_ahead_market_name="DAY_AHEAD_HOURLY",
    real_time_market_name="REAL_TIME_5_MIN",
)

# Print the first 10 rows of the resultant dataframe
print("First 10 rows of resultant dataframe:")
print(df.head(10))
