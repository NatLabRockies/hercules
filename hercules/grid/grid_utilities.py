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

    # Create an hourly version for the DA LMP (drop all periods that aren't on an hour)
    df_hr = df[df["time_utc"].dt.minute == 0].copy(deep=True)

    # Extract date and hour for use in pivot_table
    df_hr["date"] = df_hr["time_utc"].dt.date
    df_hr["hour"] = df_hr["time_utc"].dt.hour

    df_hourly = df_hr.pivot_table(
        values="DA_LMP",
        index="date",
        columns="hour",
        aggfunc="first",  # Use first value if multiple entries per hour
    )
    df_hourly = df_hourly.reindex(columns=list(range(24)))
    df_hourly = df_hourly.rename(columns={h: "DA_LMP_{:02d}".format(h) for h in df_hourly.columns})
    df_hourly = df_hourly.reset_index()

    # Add time_utc and drop date
    # Note that time _must_ be specified as UTC for Hercules
    df_hourly["time_utc"] = pd.to_datetime(df_hourly["date"], utc=True)
    df_hourly = df_hourly.drop(columns=["date"])

    df = pd.merge(df, df_hourly, on="time_utc", how="outer").ffill()

    # Add "end" rows
    df_2 = df.copy(deep=True)
    df_2["time_utc"] = df_2["time_utc"] + pd.Timedelta(seconds=5 * 60 - 1)
    df = pd.merge(df, df_2, how="outer").sort_values("time_utc").reset_index(drop=True)

    # Add time column in seconds from the first timestamp
    df["time"] = (df["time_utc"] - df["time_utc"].iloc[0]).dt.total_seconds()

    return df
