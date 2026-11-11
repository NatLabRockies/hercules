import copy

import numpy as np
import pytest
from hercules.plant_components.battery_reservoir import BatteryReservoir
from numpy.testing import assert_almost_equal

from tests.test_inputs.h_dict import h_dict_simple_battery


def make_reservoir_battery(dt=1.0, **params):
    """Build a BatteryReservoir (80 MWh, 2 MW, SOC 0.5) with inline parameter overrides."""
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["dt"] = dt
    test_h_dict["battery"]["component_type"] = "BatteryReservoir"
    test_h_dict["battery"].update(params)
    return BatteryReservoir(test_h_dict, "battery")


def step_inputs(P_avail, P_signal):
    return {
        "battery": {"power_setpoint": P_signal},
        "plant": {"locally_generated_power": P_avail},
    }


def test_BR_init():
    # Optional parameters default to an ideal battery using the full SOC window
    br = make_reservoir_battery()
    assert br.SOC == 0.5
    assert br.energy == 40000.0
    assert br.energy_min == 0.0
    assert br.energy_max == 80000.0
    assert br.power_charge_max == 2000
    assert br.power_discharge_max == 2000
    assert br.roundtrip_efficiency == 1.0
    assert br.time_constant_self_discharge == np.inf
    assert br.retention == 1.0
    assert not br.allow_grid_power_consumption
    assert br.power_charge == 0.0


def test_BR_power_constraint():
    # Setpoints beyond rated power or locally available power are clipped
    br = make_reservoir_battery()
    assert br.step(step_inputs(P_avail=3e3, P_signal=2.5e3))["battery"]["power"] == 2e3
    assert br.step(step_inputs(P_avail=3e3, P_signal=-2.5e3))["battery"]["power"] == -2e3
    assert br.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 0.25e3


def test_BR_energy_constraint():
    # Power is limited so stored energy stays within [E_min, E_max] (dt = 1 s)
    br = make_reservoir_battery()
    br.energy = br.energy_min + 500 / 3600
    out = br.step(step_inputs(P_avail=3e3, P_signal=-1.5e3))
    assert_almost_equal(out["battery"]["power"], -500)
    assert_almost_equal(br.energy, br.energy_min)

    br.energy = br.energy_max - 500 / 3600
    out = br.step(step_inputs(P_avail=3e3, P_signal=1.5e3))
    assert_almost_equal(out["battery"]["power"], 500)
    assert_almost_equal(br.energy, br.energy_max)


def test_BR_allow_grid_power_consumption():
    # Grid charging ignores locally generated power; otherwise charging is capped by it
    br = make_reservoir_battery(allow_grid_power_consumption=True)
    assert br.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 1e3

    br = make_reservoir_battery(allow_grid_power_consumption=False)
    assert br.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 0.25e3


def test_BR_charge_and_discharge_time():
    # Full discharge lasts energy_capacity / power_discharge_max = 4 h; full charge lasts
    # energy_capacity / (roundtrip_efficiency * power_charge_max) = 4000 / (0.8 * 500) = 10 h
    params = {
        "energy_capacity": 4000.0,
        "power_charge_max": 500.0,
        "power_discharge_max": 1000.0,
        "roundtrip_efficiency": 0.8,
    }

    br = make_reservoir_battery(dt=60.0, initial_conditions={"SOC": 1.0}, **params)
    powers = [
        br.step(step_inputs(P_avail=0.0, P_signal=-1000.0))["battery"]["power"] for _ in range(300)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(4.0)
    assert br.SOC == pytest.approx(0.0, abs=1e-9)

    br = make_reservoir_battery(dt=60.0, initial_conditions={"SOC": 0.0}, **params)
    powers = [
        br.step(step_inputs(P_avail=1e6, P_signal=500.0))["battery"]["power"] for _ in range(700)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(10.0)
    assert br.SOC == pytest.approx(1.0)


def test_BR_roundtrip_efficiency():
    # Charging then discharging 500 kW for 30 min each loses (1 - RTE) of the 250 kWh input
    for rte in [1.0, 0.9, 0.75]:
        br = make_reservoir_battery(dt=60.0, roundtrip_efficiency=rte)
        E0 = br.energy
        for _ in range(30):
            br.step(step_inputs(P_avail=500.0, P_signal=500.0))
        for _ in range(30):
            br.step(step_inputs(P_avail=0.0, P_signal=-500.0))
        assert br.energy == pytest.approx(E0 - 250.0 * (1 - rte))


def test_BR_self_discharge():
    # With zero power, stored energy decays exactly as exp(-t / tau)
    br = make_reservoir_battery(dt=60.0, time_constant_self_discharge=36000.0)
    for _ in range(100):
        br.step(step_inputs(P_avail=0.0, P_signal=0.0))
    assert br.SOC == pytest.approx(0.5 * np.exp(-100 * 60.0 / 36000.0))


def test_BR_self_discharge_below_min_soc():
    # SOC_min limits discharge only; an idle battery drifts below it without self-charging
    br = make_reservoir_battery(
        dt=60.0, SOC_min=0.1, time_constant_self_discharge=36000.0, initial_conditions={"SOC": 0.1}
    )
    out = br.step(step_inputs(P_avail=1e6, P_signal=0.0))
    assert out["battery"]["power"] == 0.0
    assert br.SOC == pytest.approx(0.1 * np.exp(-60.0 / 36000.0))

    # Discharge is blocked while below SOC_min
    out = br.step(step_inputs(P_avail=1e6, P_signal=-1000.0))
    assert out["battery"]["power"] == 0.0


def test_BR_discharge_duration_with_degraded_soc_window():
    # A 0.1-0.9 SOC window delivers 80% of energy_capacity: 0.8 * 4 h = 3.2 h at 1 MW
    br = make_reservoir_battery(
        dt=60.0,
        energy_capacity=4000.0,
        power_charge_max=1000.0,
        power_discharge_max=1000.0,
        roundtrip_efficiency=0.9,
        SOC_min=0.1,
        SOC_max=0.9,
        initial_conditions={"SOC": 0.9},
    )
    powers = [
        br.step(step_inputs(P_avail=0.0, P_signal=-1000.0))["battery"]["power"] for _ in range(250)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(3.2)
    assert br.SOC == pytest.approx(0.1)
