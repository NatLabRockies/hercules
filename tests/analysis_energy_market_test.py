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
