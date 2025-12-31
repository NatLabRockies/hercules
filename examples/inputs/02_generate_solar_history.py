"""Generate a simple solar input file from Flatirons 1-second data.

This script parses timestamps, creates a zero-based seconds column, and writes
the result to a feather for downstream examples.
"""

import zipfile

import pandas as pd

# Unpack the zip file containing the solar data
with zipfile.ZipFile("Flatirons_solar_data_sunset_1s.zip", "r") as zip_ref:
    zip_ref.extractall(".")

# Read raw data
df_solar = pd.read_csv("Flatirons_solar_data_sunset_1s.csv", index_col=False)

# Create UTC timestamp column, then drop original string timestamp
df_solar["time_utc"] = pd.to_datetime(df_solar["Timestamp"], format="ISO8601", utc=True)
df_solar = df_solar.drop(columns=["Timestamp"])

# Clean index and finalize columns
df_solar = df_solar.reset_index(drop=True)

# Save the data
df_solar.to_feather("solar_input.ftr")

print(f"First time (UTC): {df_solar['time_utc'].iloc[0]}")
print(f"Last time (UTC): {df_solar['time_utc'].iloc[-1]}")
