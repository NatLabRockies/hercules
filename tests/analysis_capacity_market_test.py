"""Tests for hercules.analysis.capacity_market."""

import pytest
from hercules.analysis import capacity_market

from tests.test_inputs.analysis_output import build_hercules_output

# Small two-season region: summer (Jun-Aug, 92 days) and winter (Dec-Feb, 90 days in 2026)
REGION = {
    "seasons": {"summer": [6, 7, 8], "winter": [12, 1, 2]},
    "accreditation_fraction": {
        "battery": {"summer": 0.9, "winter": 0.5},
        "solar": {"summer": 0.04, "winter": 0.01},
    },
    "capacity_price_USD_per_MW_day": {
        2025: {1: {"summer": 100.0, "winter": 10.0}},
        2026: {1: {"summer": 200.0, "winter": 20.0}},
    },
}
H_DICT = {
    "plant": {"interconnect_limit": 1000.0},
    "battery": {"component_type": "BatteryReservoir", "power_discharge_max": 100.0},
    "solar": {"component_type": "SolarPySAMPVWatts", "capacity_rated": 1500.0},
}


def test_accredited_capacity_by_season_and_annual(tmp_path):
    # 100 kW battery: 0.09 MW summer, 0.05 MW winter; day-weighted mean over 92 + 90 days.
    ho = build_hercules_output(tmp_path, {"battery.power": [0.0]}, H_DICT)
    seasonal = capacity_market.compute_capacity_accredited_seasonal_MW(ho, REGION, "battery")
    assert seasonal == pytest.approx({"summer": 0.09, "winter": 0.05})
    annual = capacity_market.compute_capacity_accredited_MW(ho, REGION, "battery")
    assert annual == pytest.approx((0.09 * 92 + 0.05 * 90) / 182)


def test_accredited_capacity_capped_at_POI(tmp_path):
    # The 1500 kW solar rating is capped at the 1000 kW interconnect limit.
    ho = build_hercules_output(tmp_path, {"solar.power": [0.0]}, H_DICT)
    seasonal = capacity_market.compute_capacity_accredited_seasonal_MW(ho, REGION, "solar")
    assert seasonal == pytest.approx({"summer": 0.04, "winter": 0.01})


def test_capacity_revenue(tmp_path):
    # Latest price year (2026): 0.09 MW x 200 $/MW-day x 92 + 0.05 MW x 20 $/MW-day x 90.
    ho = build_hercules_output(tmp_path, {"battery.power": [0.0]}, H_DICT)
    revenue = capacity_market.compute_revenue_capacity_annual(ho, REGION, 1, "battery")
    assert revenue == pytest.approx(0.09 * 200 * 92 + 0.05 * 20 * 90)
    revenue_2025 = capacity_market.compute_revenue_capacity_annual(ho, REGION, 1, "battery", 2025)
    assert revenue_2025 == pytest.approx(0.09 * 100 * 92 + 0.05 * 10 * 90)
    with pytest.raises(ValueError, match="Unknown zone"):
        capacity_market.compute_revenue_capacity_annual(ho, REGION, 2, "battery")
