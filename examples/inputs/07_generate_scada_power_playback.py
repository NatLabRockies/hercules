"""Generate a history of power playback data"""

import pandas as pd

rated_power = 15000
starttime_utc = pd.to_datetime("2020-01-01T00:00:00Z", utc=True)  # Midnight Jan 1, 2020 UTC
endtime_utc = pd.to_datetime("2020-01-01T00:15:50Z", utc=True)  # 15 minutes 50 seconds later

# Create a dataframe with the power playback data
df = pd.DataFrame(index=pd.date_range(start=starttime_utc, end=endtime_utc, freq="S"))
df["power"] = rated_power

# Set power to 0 for first half of the data
df.loc[df.index < pd.to_datetime("2020-01-01T00:07:30Z", utc=True), "power"] = 0

# Reset the index and name the time column "time_utc"
df = df.reset_index()
df = df.rename(columns={"index": "time_utc"})

# Save to a feather file
df.to_feather("power_playback_input.ftr")
