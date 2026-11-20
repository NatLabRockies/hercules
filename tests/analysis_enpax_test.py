"""Tests for hercules.analysis.enpax."""

import pytest
import yaml
from hercules.analysis import enpax

from tests.test_inputs.analysis_output import build_hercules_output

# Two-season region with summer (92 days) and winter (90 days in 2026)
REGION = {
    "name": "TEST",
    "seasons": {"summer": [6, 7, 8], "winter": [12, 1, 2]},
    "accreditation_fraction": {
        "battery": {"summer": 0.9, "winter": 0.5},
        "solar": {"summer": 0.04, "winter": 0.01},
    },
    "capacity_price_USD_per_MW_day": {2026: {1: {"summer": 200.0, "winter": 20.0}}},
}
H_DICT = {
    "plant": {"interconnect_limit": 1000.0},
    "solar": {
        "component_type": "SolarPySAMPVWatts",
        "capacity_rated": 800.0,
        "DC_capacity_rated": 1000.0,
    },
    "battery": {
        "component_type": "BatteryReservoir",
        "power_discharge_max": 500.0,
        "energy_capacity": 2000.0,
    },
}


def test_build_and_write_enpax_case(tmp_path):
    # Two hours (annualized x 4380): solar 0.8 MWh at RT 10 $/MWh; battery discharges 0.5 MWh,
    # all cleared DA at 40 $/MWh.
    ho = build_hercules_output(
        tmp_path,
        {
            "solar.power": [800.0, 0.0],
            "battery.power": [0.0, 500.0],
            "controller.battery.power_cleared_DA": [float("nan"), 500.0],
            "external_signals.LMP_RT": [10.0, 20.0],
            "external_signals.LMP_DA": [30.0, 40.0],
        },
        H_DICT,
        dt=3600.0,
    )
    case = enpax.write_enpax_case_yaml(ho, tmp_path / "case.yaml", REGION, 1)
    with open(tmp_path / "case.yaml") as f:
        assert yaml.safe_load(f) == case

    assert case["plant"] == pytest.approx(
        {"interconnect_limit_MW": 1.0, "energy_annual_MWh": 1.3 * 4380, "price_year": 2026}
    )
    solar = case["components"]["solar"]
    assert solar == pytest.approx(
        {
            "type": "solar",
            "DC_capacity_rated_MW": 1.0,
            "capacity_rated_MW": 0.8,
            "energy_annual_MWh": 0.8 * 4380,
            "revenue_energy_annual_USD": 8.0 * 4380,
            "revenue_capacity_annual_USD": 0.032 * 200 * 92 + 0.008 * 20 * 90,
            "capacity_accredited_MW": (0.032 * 92 + 0.008 * 90) / 182,
        }
    )
    battery = case["components"]["battery"]
    assert battery == pytest.approx(
        {
            "type": "battery",
            "DC_capacity_rated_MW": None,
            "capacity_rated_MW": 0.5,
            "energy_capacity_MWh": 2.0,
            "duration_hours": 4.0,
            "energy_discharged_annual_MWh": 0.5 * 4380,
            "cycle_count_equivalent_annual": 0.25 * 4380,
            "revenue_energy_annual_USD": 20.0 * 4380,
            "revenue_capacity_annual_USD": 0.45 * 200 * 92 + 0.25 * 20 * 90,
            "capacity_accredited_MW": (0.45 * 92 + 0.25 * 90) / 182,
        }
    )
