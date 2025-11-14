import pandas as pd
import pytest
from hercules.grid.grid_utilities import (
    generate_locational_marginal_price_dataframe_from_gridstatus,
)


def test_generate_locational_marginal_price_dataframe_from_gridstatus():

    df_da = pd.DataFrame(
        data = {
            "interval_start_utc": pd.date_range(start="2024-01-01", periods=5, freq="h"),
            "market": ["DAY_AHEAD_HOURLY"] * 5,
            "lmp": [10, 20, 30, 40, 50],
        }
    )

    df_rt = pd.DataFrame(
        data = {
            "interval_start_utc": pd.date_range(start="2024-01-01", periods=12, freq="5min"),
            "market": ["REAL_TIME_5_MIN"] * 12,
            "lmp": [15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125],
        }
    )

    df_out = generate_locational_marginal_price_dataframe_from_gridstatus(df_da, df_rt)

    assert "time_utc" in df_out.columns
    assert "lmp_rt" in df_out.columns
    assert "lmp_da" in df_out.columns
    for hour in range(24):
        assert f"lmp_da_{hour:02d}" in df_out.columns

    # Check dt in output (should be one second less than five minutes; then 1 second)
    assert (df_out["time_utc"].iloc[1] - df_out["time_utc"].iloc[0]).total_seconds() == 299
    assert (df_out["time_utc"].iloc[2] - df_out["time_utc"].iloc[1]).total_seconds() == 1

    # Check that the values covered are the union of the inputs
    assert df_out["time_utc"].min() <= df_da["interval_start_utc"].min()
    assert df_out["time_utc"].min() <= df_rt["interval_start_utc"].min()
    assert df_out["time_utc"].max() >= df_da["interval_start_utc"].max()
    assert df_out["time_utc"].max() >= df_rt["interval_start_utc"].max()

    # Check that error is raised if intervals don't overlap at all
    df_da_no_overlap = df_da.copy()
    df_da_no_overlap["interval_start_utc"] = pd.date_range(start="2023-12-25", periods=5, freq="h")
    with pytest.raises(ValueError):
        generate_locational_marginal_price_dataframe_from_gridstatus(
            df_da_no_overlap,
            df_rt
        )
    
    # Check that a different market name also works
    df_da_diff_market = df_da.copy()
    df_da_diff_market["market"] = ["CUSTOM_DA_MARKET"] * 5

    df_out_2 = generate_locational_marginal_price_dataframe_from_gridstatus(
        df_da_diff_market,
        df_rt,
        day_ahead_market_name="CUSTOM_DA_MARKET"
    )

    assert df_out_2.equals(df_out)

    # Check that error is raised if markets are not all consistent
    df_da_diff_market.loc[df_da_diff_market.index[0], "market"] = "ANOTHER_MARKET"
    with pytest.raises(ValueError):
        generate_locational_marginal_price_dataframe_from_gridstatus(
            df_da_diff_market,
            df_rt,
            day_ahead_market_name="CUSTOM_DA_MARKET"
        )

    # Check that a different (valid) time interval works for real-time data
    df_rt_15 = pd.DataFrame(
        data = {
            "interval_start_utc": pd.date_range(start="2024-01-01", periods=4, freq="15min"),
            "market": ["REAL_TIME_15_MIN"] * 4,
            "lmp": [15, 45, 75, 105],
        }
    )
    df_out_3 = generate_locational_marginal_price_dataframe_from_gridstatus(
        df_da,
        df_rt_15,
        real_time_market_name="REAL_TIME_15_MIN"
    )

    assert (df_out_3["time_utc"].iloc[1] - df_out_3["time_utc"].iloc[0]).total_seconds() == 899
    assert (df_out_3["time_utc"].iloc[2] - df_out_3["time_utc"].iloc[1]).total_seconds() == 1

    # Check that an invalid time interval raises an error
    df_rt_invalid = pd.DataFrame(
        data = {
            "interval_start_utc": pd.date_range(start="2024-01-01", periods=4, freq="7min"),
            "market": ["REAL_TIME_7_MIN"]* 4,
            "lmp": [15, 45, 75, 105],
        }
    )
    with pytest.raises(ValueError):
        generate_locational_marginal_price_dataframe_from_gridstatus(
            df_da,
            df_rt_invalid,
            real_time_market_name="REAL_TIME_7_MIN"
        )
