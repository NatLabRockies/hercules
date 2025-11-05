import pandas as pd


def generate_locational_marginal_price_dataframe(df_day_ahead_lmp, df_real_time_lmp):
    """
    Create a dataframe containing the day ahead price forecast and the real time price
    at five-minute intervals.

    Input dataframes must contain the following columns:
        interval_start_utc (UTC time for the row)
        market (REAL_TIME_5_MIN or DAY_AHEAD_HOURLY)
        lmp (price of the market for that five-minute interval)

    The RT dataframe is assumed to have five-minute time resolution, while the DA dataframe
    is assumed to have hourly time resolution.
    Assumes that both dataframe begins at 00:00 UTC on the first day
    (e.g. yyyy-mm-dd 00:00:00+00:00) TODO: Is that ok? how should UTC offset be handled?

    Returns a dataframe with the RT LMP and DA LMP at five-minute intervals, along with
    the DA LMP for each hour in separate columns. For use as external data in Hercules.

    Args:
        df_day_ahead_lmp (pd.DataFrame): DataFrame with day ahead data
        df_real_time_lmp (pd.DataFrame): DataFrame with real time data

    Returns:
        pd.DataFrame: DataFrame with columns
            'time', 'RT_LMP', 'DA_LMP', 'DA_LMP_00', ..., 'DA_LMP_23'
    """
    # Check correct market on each
    if df_day_ahead_lmp["market"].unique() != ["DAY_AHEAD_HOURLY"]:
        raise ValueError("df_day_ahead_lmp must only contain DAY_AHEAD_HOURLY market data.")
    if df_real_time_lmp["market"].unique() != ["REAL_TIME_5_MIN"]:
        raise ValueError("df_real_time_lmp must only contain REAL_TIME_5_MIN market data.")

    # TODO: Add checks that dataframes cover the same time period, have no missing data, etc.
    # TODO: How do we handle dataframes where the first row is not 00:00 UTC?
    # TODO: Should DA_LMP_00 be _local_ midnight? How can we handle that? It may not matter?

    # Trim and rename
    df_da = df_day_ahead_lmp[["interval_start_utc", "lmp"]].rename(
        columns={"interval_start_utc": "time_utc", "lmp": "DA_LMP"}
    )
    df_rt = df_real_time_lmp[["interval_start_utc", "lmp"]].rename(
        columns={"interval_start_utc": "time_utc", "lmp": "RT_LMP"}
    )
    # Merge on time_utc
    df = pd.merge(df_da, df_rt, on="time_utc", how="outer").ffill()
    df["time_utc"] = pd.to_datetime(df["time_utc"])

    # Create a rolling hourly version for the DA LMP
    df_rolling_hourly = df.copy()
    
    # For each 5-minute interval, create 24 rolling hourly columns (forward-looking)
    periods_per_hour = 12 # TODO: avoid hardcoding this.
    for offset_hour in range(24):
        shift_amount = -offset_hour * periods_per_hour
        
        # Use shift to get values from h hours in the future
        df_rolling_hourly[f"DA_LMP_rolling_{offset_hour:02d}"] = df_rolling_hourly["DA_LMP"].shift(shift_amount)
    
    # Keep only the rolling columns and time
    rolling_cols = ["time_utc"] + [f"DA_LMP_rolling_{h:02d}" for h in range(24)]
    df_hourly = df_rolling_hourly[rolling_cols].copy()
    
    # Rename columns to match expected format (removing 'rolling_' prefix)
    rename_dict = {f"DA_LMP_rolling_{h:02d}": f"DA_LMP_{h:02d}" for h in range(24)}
    df_hourly = df_hourly.rename(columns=rename_dict)

    df = pd.merge(df, df_hourly, on="time_utc", how="outer").ffill()

    # Add "end" rows
    df_2 = df.copy(deep=True)
    df_2["time_utc"] = df_2["time_utc"] + pd.Timedelta(seconds=5 * 60 - 1)
    df = pd.merge(df, df_2, how="outer").sort_values("time_utc").reset_index(drop=True)

    return df
