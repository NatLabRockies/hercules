"""Tests for hercules.analysis.energy_market."""

import pytest
from hercules.analysis import energy_market

from tests.test_inputs.analysis_output import build_hercules_output

H_DICT = {
    "plant": {"interconnect_limit": 1500.0},
    "solar": {"component_type": "SolarPySAMPVWatts"},
}


def test_revenue_RT_and_DA_use_POI_limited_export(tmp_path):
    # 2000 kW is limited to 1500 kW: 1 MWh at 10 $/MWh + 1.5 MWh at 20 $/MWh = $40 RT;
    # at DA prices 30 and 40 $/MWh, $90.
    ho = build_hercules_output(
        tmp_path,
        {
            "solar.power": [1000.0, 2000.0],
            "external_signals.LMP_RT": [10.0, 20.0],
            "external_signals.LMP_DA": [30.0, 40.0],
        },
        H_DICT,
        dt=3600.0,
    )
    with pytest.warns(UserWarning):
        assert energy_market.compute_revenue_RT_total(ho) == pytest.approx(40.0)
    assert energy_market.compute_revenue_DA_total(ho) == pytest.approx(90.0)
    assert energy_market.compute_revenue_RT_annual(ho) == pytest.approx(40.0 * 8760 / 2)
    assert energy_market.compute_revenue_DA_annual(ho) == pytest.approx(90.0 * 8760 / 2)


def test_revenue_charging_is_a_cost(tmp_path):
    # Charging 1000 kW for 1 h at 10 $/MWh costs $10.
    ho = build_hercules_output(
        tmp_path,
        {"battery.power": [-1000.0], "external_signals.LMP_RT": [10.0]},
        {
            "plant": {"interconnect_limit": 1500.0},
            "battery": {"component_type": "BatteryReservoir"},
        },
        dt=3600.0,
    )
    assert energy_market.compute_revenue_RT_total(ho, "battery.power") == pytest.approx(-10.0)


def test_revenue_two_settlement(tmp_path):
    # Hour 1: 1.5 MWh cleared at DA 30 $/MWh ($45), 0.5 MWh short bought back at RT 10 (-$5).
    # Hour 2: nothing cleared (NaN), 2 MWh at RT 20 $/MWh ($40).
    ho = build_hercules_output(
        tmp_path,
        {
            "solar.power": [1000.0, 2000.0],
            "solar.power_cleared_DA": [1500.0, float("nan")],
            "external_signals.LMP_RT": [10.0, 20.0],
            "external_signals.LMP_DA": [30.0, 40.0],
        },
        {"plant": {"interconnect_limit": 3000.0}, "solar": H_DICT["solar"]},
        dt=3600.0,
    )
    totals = energy_market.compute_revenue_two_settlement_total(
        ho, "solar.power", "solar.power_cleared_DA"
    )
    assert totals == pytest.approx((80.0, 45.0, 35.0))
    annual = energy_market.compute_revenue_two_settlement_annual(
        ho, "solar.power", "solar.power_cleared_DA"
    )
    assert annual == pytest.approx(tuple(v * 8760 / 2 for v in totals))

    energy_market.add_revenue_two_settlement_columns(ho, "solar.power", "solar.power_cleared_DA")
    assert list(ho.df["analysis.solar.power_revenue_DA"]) == pytest.approx([45.0, 0.0])
    assert list(ho.df["analysis.solar.power_revenue_RT"]) == pytest.approx([-5.0, 40.0])


def test_revenue_TBX_hourly(tmp_path):
    # Day 1 prices are 0..23 $/MWh; day 2 is flat at 50 $/MWh. For a 2 MW, 4 h battery:
    # TB4 day 1 = (20+21+22+23) - (0+1+2+3) = 80 $/MW; day 2 = 0.
    prices = list(range(24)) + [50.0] * 24
    ho = build_hercules_output(
        tmp_path,
        {"external_signals.LMP_DA": prices},
        {"plant": {"interconnect_limit": 1.0}},
        dt=3600.0,
    )
    assert energy_market.compute_revenue_TBX_total(ho, 2000.0) == pytest.approx(160.0)
    assert energy_market.compute_revenue_TBX_annual(ho, 2000.0) == pytest.approx(160.0 * 8760 / 48)

    # Efficiency 0.75 charges 5.33 h: 0+1+2+3+4 + 0.33 x 5; day 2 still earns 0.
    total = energy_market.compute_revenue_TBX_total(ho, 2000.0, roundtrip_efficiency=0.75)
    assert total == pytest.approx(2 * (86 - 10 - 5 / 3))

    # Efficiency 0.5 loses 200 $/MW on day 2, kept only without skipping.
    total = energy_market.compute_revenue_TBX_total(
        ho, 2000.0, roundtrip_efficiency=0.5, allow_skip=False
    )
    assert total == pytest.approx(2 * ((86 - 28) - 200))


def test_revenue_TBX_sub_hourly_blocks(tmp_path):
    # One day at 5 min: 120 $/MWh for the first half of hours 10 and 14, otherwise 0.
    # Hourly blocks see two 60 $/MWh hours (TB1 = 60 $/MW); 5 min blocks find a full hour at
    # 120 $/MWh (12 blocks).
    prices = [0.0] * 288
    for start in (120, 168):
        prices[start : start + 6] = [120.0] * 6
    ho = build_hercules_output(
        tmp_path,
        {"external_signals.LMP_RT": prices},
        {"plant": {"interconnect_limit": 1.0}},
        dt=300.0,
    )
    kwargs = {"duration_hours": 1.0, "LMP_column": "external_signals.LMP_RT"}
    assert energy_market.compute_revenue_TBX_total(ho, 1000.0, **kwargs) == pytest.approx(60.0)
    total = energy_market.compute_revenue_TBX_total(ho, 1000.0, block_minutes=5, **kwargs)
    assert total == pytest.approx(120.0)


def test_revenue_TBX_day_timezone(tmp_path):
    # 100 $/MWh from 02:00 to 06:00 UTC on 2024-01-01, which is 2023-12-31 in US/Central.
    # UTC days earn 400 $/MW; Central days earn 0 (Dec 31 has too few hours and is dropped).
    prices = [0.0] * 48
    prices[2:6] = [100.0] * 4
    ho = build_hercules_output(
        tmp_path,
        {"external_signals.LMP_DA": prices},
        {"plant": {"interconnect_limit": 1.0}},
        dt=3600.0,
    )
    assert energy_market.compute_revenue_TBX_total(ho, 1000.0) == pytest.approx(400.0)
    total = energy_market.compute_revenue_TBX_total(ho, 1000.0, day_timezone="US/Central")
    assert total == pytest.approx(0.0)
