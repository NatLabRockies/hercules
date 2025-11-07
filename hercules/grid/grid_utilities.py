import pandas as pd


def generate_locational_marginal_price_dataframe_from_gridstatus(
        df_day_ahead_lmp: pd.DataFrame,
        df_real_time_lmp: pd.DataFrame,
        day_ahead_market_name: str="DAY_AHEAD_HOURLY",
        real_time_market_name: str="REAL_TIME_5_MIN",
    ):
    """
    Create a dataframe containing the day ahead price forecast and the real time price
    at real-time price intervals.

    Input dataframes must contain the following columns:
        interval_start_utc (UTC time for the row)
        market (REAL_TIME_5_MIN, DAY_AHEAD_HOURLY, etc)
        lmp (price of the market for that interval)

    The RT dataframe is assumed to have minute time resolution, while the DA dataframe
    is assumed to have hourly time resolution.

    Returns a dataframe with the RT LMP and DA LMP at the base intervals, along with
    the DA LMP for each future hour over the next 24 hours in separate columns. For use as external
    data in Hercules.

    Args:
        df_day_ahead_lmp (pd.DataFrame): DataFrame with day ahead data
        df_real_time_lmp (pd.DataFrame): DataFrame with real time data
        day_ahead_market_name (str): Market name for day ahead data
        real_time_market_name (str): Market name for real time data

    Returns:
        pd.DataFrame: DataFrame with columns
            "time_utc", "RT_LMP", "DA_LMP", "DA_LMP_00", ..., "DA_LMP_23"
    """
    # Check correct market on each
    if df_day_ahead_lmp["market"].unique() != [day_ahead_market_name]:
        raise ValueError(f"df_day_ahead_lmp must only contain {day_ahead_market_name} market data.")
    if df_real_time_lmp["market"].unique() != [real_time_market_name]:
        raise ValueError(f"df_real_time_lmp must only contain {real_time_market_name} market data.")

    # Trim and rename
    df_da = df_day_ahead_lmp[["interval_start_utc", "lmp"]].rename(
        columns={"interval_start_utc": "time_utc", "lmp": "DA_LMP"}
    )
    df_rt = df_real_time_lmp[["interval_start_utc", "lmp"]].rename(
        columns={"interval_start_utc": "time_utc", "lmp": "RT_LMP"}
    )

    # Ensure datetime format
    df_da["time_utc"] = pd.to_datetime(df_da["time_utc"])
    df_rt["time_utc"] = pd.to_datetime(df_rt["time_utc"])

    # Check that there is an overlap between time ranges
    if (
        max(df_da["time_utc"].min(), df_rt["time_utc"].min())
        >= min(df_da["time_utc"].max(), df_rt["time_utc"].max())
    ):
        raise ValueError(
            f"No time overlap between day-ahead and real-time data.\n"
            f"Day-ahead range: {df_da.time_utc.min()} to {df_da.time_utc.max()}.\n"
            f"Real-time range: {df_rt.time_utc.min()} to {df_rt.time_utc.max()}."
        )

    # Merge on time_utc
    df = pd.merge(df_da, df_rt, on="time_utc", how="outer").ffill()

    # Get time step for merged data
    dt = (df["time_utc"].iloc[1] - df["time_utc"].iloc[0]).total_seconds()

    # Create 24 rolling hourly columns (forward-looking)
    periods_per_hour = 3600 / dt
    if not periods_per_hour.is_integer():
        raise ValueError(
            f"Data time step of {dt} seconds is not compatible with hourly periods."
        )
    periods_per_hour = int(periods_per_hour)

    for h in range(24):
        h_shift = -h * periods_per_hour
        df[f"DA_LMP_{h:02d}"] = df["DA_LMP"].shift(h_shift)

    # Add rows representing the end of each interval for step-like interpolation
    df_2 = df.copy(deep=True)
    df_2["time_utc"] = df_2["time_utc"] + pd.Timedelta(seconds=dt - 1)
    df = pd.merge(df, df_2, how="outer").sort_values("time_utc").reset_index(drop=True)

    return df
