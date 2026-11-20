"""Tests for hercules.analysis.storage."""

import pytest
from hercules.analysis import storage

from tests.test_inputs.analysis_output import build_hercules_output

H_DICT = {
    "plant": {"interconnect_limit": 1000.0},
    "battery": {"component_type": "BatteryReservoir", "energy_capacity": 200.0},
}


def test_energy_discharged_and_cycles(tmp_path):
    # 100 kW discharged for 2 h of a 4 h run on a 200 kWh battery: 0.2 MWh, one cycle.
    ho = build_hercules_output(
        tmp_path,
        {"battery.power": [100.0, -50.0, 100.0, 0.0], "battery.SOC": [0.5, 0.75, 0.25, 0.25]},
        H_DICT,
        dt=3600.0,
    )
    assert storage.compute_energy_discharged_total_MWh(ho) == pytest.approx(0.2)
    assert storage.compute_energy_discharged_annual_MWh(ho) == pytest.approx(0.2 * 8760 / 4)
    assert storage.compute_cycle_count_equivalent_total(ho) == pytest.approx(1.0)
    assert storage.compute_cycle_count_equivalent_annual(ho) == pytest.approx(8760 / 4)


def test_SOC_metrics(tmp_path):
    # SOC 0.5 -> 1.0 -> 0.5 -> 0.0: decreases sum to 1.0, absolute changes to 1.5.
    ho = build_hercules_output(
        tmp_path,
        {"battery.power": [0.0] * 4, "battery.SOC": [0.5, 1.0, 0.5, 0.0]},
        H_DICT,
        dt=3600.0,
    )
    assert storage.compute_cycle_count_equivalent_SOC_total(ho) == pytest.approx(1.0)
    assert storage.compute_cycle_count_equivalent_SOC_annual(ho) == pytest.approx(8760 / 4)
    assert storage.compute_SOC_mileage_total(ho) == pytest.approx(1.5)
    assert storage.compute_SOC_mileage_annual(ho) == pytest.approx(1.5 * 8760 / 4)
    assert storage.compute_SOC_mean(ho) == pytest.approx(0.5)


def test_rainflow_damage(tmp_path):
    # SOC 0 -> 0.5 -> 0.3 -> 0.6 -> 0: one closed 0.2 cycle and two 0.6 half cycles,
    # so damage = 0.2**2 + 2 * 0.5 * 0.6**2 = 0.4.
    ho = build_hercules_output(
        tmp_path,
        {"battery.power": [0.0] * 5, "battery.SOC": [0.0, 0.5, 0.3, 0.6, 0.0]},
        H_DICT,
        dt=3600.0,
    )
    assert storage.compute_rainflow_damage_total(ho) == pytest.approx(0.4)
    assert storage.compute_rainflow_damage_total(ho, depth_exponent=1.0) == pytest.approx(0.8)
    assert storage.compute_rainflow_damage_annual(ho) == pytest.approx(0.4 * 8760 / 5)
