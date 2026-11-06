import copy

import numpy as np
import pytest
from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from numpy.testing import assert_almost_equal, assert_array_almost_equal

from tests.test_inputs.h_dict import h_dict_lib_battery, h_dict_simple_battery


def make_simple_battery(dt=1.0, **params):
    """Build a BatterySimple (80 MWh, 2 MW, SOC 0.5) with inline parameter overrides."""
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["dt"] = dt
    test_h_dict["battery"].update(params)
    return BatterySimple(test_h_dict, "battery")


def create_LIB():
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    return BatteryLithiumIon(test_h_dict, "battery")


@pytest.fixture
def LI():
    return create_LIB()


def step_inputs(P_avail, P_signal):
    return dict(
        {
            "battery": {"power_setpoint": P_signal},
            "plant": {"locally_generated_power": P_avail},
        }
    )


def test_SB_init():
    # Optional parameters default to an ideal battery using the full SOC window
    sb = make_simple_battery()
    assert sb.SOC == 0.5
    assert sb.E == 40000.0
    assert sb.E_min == 0.0
    assert sb.E_max == 80000.0
    assert sb.charge_rate == 2000
    assert sb.discharge_rate == 2000
    assert sb.roundtrip_efficiency == 1.0
    assert sb.tau_self_discharge == np.inf
    assert sb.decay == 1.0
    assert not sb.allow_grid_power_consumption
    assert sb.power_kw == 0.0


def test_SB_removed_usage_keys_raise():
    # Removed usage-tracking inputs fail loudly rather than being silently ignored
    with pytest.raises(ValueError, match="track_usage"):
        make_simple_battery(track_usage=True)


def test_SB_power_constraint():
    # Setpoints beyond rated power or locally available power are clipped
    sb = make_simple_battery()
    assert sb.step(step_inputs(P_avail=3e3, P_signal=2.5e3))["battery"]["power"] == 2e3
    assert sb.step(step_inputs(P_avail=3e3, P_signal=-2.5e3))["battery"]["power"] == -2e3
    assert sb.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 0.25e3


def test_SB_energy_constraint():
    # Power is limited so stored energy stays within [E_min, E_max] (dt = 1 s)
    sb = make_simple_battery()
    sb.E = sb.E_min + 500 / 3600
    out = sb.step(step_inputs(P_avail=3e3, P_signal=-1.5e3))
    assert_almost_equal(out["battery"]["power"], -500)
    assert_almost_equal(sb.E, sb.E_min)

    sb.E = sb.E_max - 500 / 3600
    out = sb.step(step_inputs(P_avail=3e3, P_signal=1.5e3))
    assert_almost_equal(out["battery"]["power"], 500)
    assert_almost_equal(sb.E, sb.E_max)


def test_LI_init():
    """Test init"""
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    LI = BatteryLithiumIon(test_h_dict, "battery")
    assert LI.dt == test_h_dict["dt"]
    assert LI.SOC == test_h_dict["battery"]["initial_conditions"]["SOC"]
    assert LI.SOC_min == test_h_dict["battery"]["min_SOC"]
    assert LI.SOC_max == test_h_dict["battery"]["max_SOC"]
    assert_almost_equal(LI.P_min, -2000, 6)
    assert_almost_equal(LI.P_max, 2000, 6)
    assert LI.P_max > LI.P_min
    assert LI.energy_capacity == test_h_dict["battery"]["energy_capacity"]


def test_LI_post_init():
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    LI = BatteryLithiumIon(test_h_dict, "battery")
    assert LI.SOH == 1
    assert LI.T == 25
    assert LI.x == 0
    assert LI.V_RC == 0
    assert LI.error_sum == 0
    assert LI.n_cells == 1538615.4000015387
    assert LI.C == 19543.890000806812
    assert LI.V_bat_nom == 4093.350914106529
    assert LI.I_bat_max == 488.5972500201703


def test_LI_OCV(LI):
    LI.SOC = 0.25
    assert_almost_equal(LI.OCV(), 3.2654698427383457, decimal=4)

    LI.SOC = 0.75
    assert_almost_equal(LI.OCV(), 3.316731143986497, decimal=4)


def test_LI_build_SS(LI):
    """Check ABCD matrices for different conditions"""

    assert_array_almost_equal(
        LI.build_SS(),
        [-0.017767729688006585, 1, 7.533462876320113e-05, 0.002720095833999999],
        5,
    )

    LI.SOC = 0.75
    LI.SOH = 0.75
    LI.T = 10
    assert_array_almost_equal(
        LI.build_SS(),
        [-0.026421742559794213, 1, 0.00012815793568836145, 0.00555564775],
        5,
    )


def test_LI_step_cell(LI):
    # check RC branch step response
    V_RC = np.zeros(5)
    for i in range(5):
        V_RC[i] = LI.V_RC
        LI.step_cell(10)

    assert_array_almost_equal(
        V_RC,
        [
            0.0,
            0.02720095833999999,
            0.027954304627632,
            0.028694265662063904,
            0.029421079268856364,
        ],
        5,
    )


def test_LI_calc_power(LI):
    assert_almost_equal(LI.calc_power(400), 1593832.1960216616, decimal=-2)

    LI.SOC = 0.75
    assert_almost_equal(LI.calc_power(400), 1645641.7527372995, decimal=-2)

    LI.step_cell(10)
    assert_almost_equal(LI.calc_power(400), 1658686.3702462215, decimal=-2)


def test_LI_step(LI):
    P_avail = 1.5e3
    P_signal = 1e3

    out = LI.step(step_inputs(P_avail=P_avail, P_signal=P_signal))

    assert_almost_equal(out["battery"]["power"], P_signal, 0)
    assert_almost_equal(LI.SOC, 0.10200356700632712, decimal=5)
    assert_almost_equal(LI.V_RC, 0.0005503468409411925, decimal=5)


def test_LI_control(LI):
    P_avail = 1.5e3
    P_signal = 1e3
    I_charge, I_reject = LI.control(P_signal, P_avail)
    assert_almost_equal(LI.calc_power(I_charge), P_signal * 1e3, 0)

    # check that the integrator offset improves setpoint tracking as the simulation proceeds
    out1 = LI.step(step_inputs(P_avail, P_signal))
    for i in range(10):
        LI.step(step_inputs(P_avail, P_signal))
    out2 = LI.step(step_inputs(P_avail, P_signal))

    assert np.abs(out1["battery"]["reject"]) >= np.abs(out2["battery"]["reject"])


def test_LI_constraints(LI):
    # no constraints applied
    I_charge, I_reject = LI.constraints(I_signal=400, I_avail=500)
    assert I_charge == 400
    assert I_reject == 0

    # I_avail is insufficient
    I_charge, I_reject = LI.constraints(I_signal=400, I_avail=300)
    assert I_charge == 300
    assert I_reject == 100

    # I_signal is above max charginging rate
    I_charge, I_reject = LI.constraints(I_signal=500, I_avail=1e3)
    assert I_charge == 488.5972500201703
    assert I_reject == 11.402749979829707

    # I_signal will charge the battery beyond max SOC
    LI.charge = LI.charge_max - 0.05
    I_charge, I_reject = LI.constraints(I_signal=400, I_avail=400)
    assert I_charge == 179.99999999738066
    assert I_reject == 220.00000000261934

    # I_signal is beyond max discharginging rate
    I_charge, I_reject = LI.constraints(I_signal=-500, I_avail=0)
    assert I_charge == -488.5972500201703
    assert I_reject == -11.402749979829707

    # I_signal will charge the battery below min SOC
    LI.charge = LI.charge_min + 0.05
    I_charge, I_reject = LI.constraints(I_signal=-400, I_avail=0)
    assert I_charge == -179.9999999998363
    assert I_reject == -220.0000000001637


def test_SB_allow_grid_power_consumption():
    # Grid charging ignores locally generated power; otherwise charging is capped by it
    sb = make_simple_battery(allow_grid_power_consumption=True)
    assert sb.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 1e3

    sb = make_simple_battery(allow_grid_power_consumption=False)
    assert sb.step(step_inputs(P_avail=0.25e3, P_signal=1e3))["battery"]["power"] == 0.25e3


def test_SB_charge_and_discharge_time():
    # Full discharge lasts energy_capacity / discharge_rate = 4 h; full charge lasts
    # energy_capacity / (roundtrip_efficiency * charge_rate) = 4000 / (0.8 * 500) = 10 h
    params = {
        "energy_capacity": 4000.0,
        "charge_rate": 500.0,
        "discharge_rate": 1000.0,
        "roundtrip_efficiency": 0.8,
    }

    sb = make_simple_battery(dt=60.0, initial_conditions={"SOC": 1.0}, **params)
    powers = [
        sb.step(step_inputs(P_avail=0.0, P_signal=-1000.0))["battery"]["power"] for _ in range(300)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(4.0)
    assert sb.SOC == pytest.approx(0.0, abs=1e-9)

    sb = make_simple_battery(dt=60.0, initial_conditions={"SOC": 0.0}, **params)
    powers = [
        sb.step(step_inputs(P_avail=1e6, P_signal=500.0))["battery"]["power"] for _ in range(700)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(10.0)
    assert sb.SOC == pytest.approx(1.0)


def test_SB_roundtrip_efficiency():
    # Charging then discharging 500 kW for 30 min each loses (1 - RTE) of the 250 kWh input
    for rte in [1.0, 0.9, 0.75]:
        sb = make_simple_battery(dt=60.0, roundtrip_efficiency=rte)
        E0 = sb.E
        for _ in range(30):
            sb.step(step_inputs(P_avail=500.0, P_signal=500.0))
        for _ in range(30):
            sb.step(step_inputs(P_avail=0.0, P_signal=-500.0))
        assert sb.E == pytest.approx(E0 - 250.0 * (1 - rte))


def test_SB_self_discharge():
    # With zero power, stored energy decays exactly as exp(-t / tau)
    sb = make_simple_battery(dt=60.0, self_discharge_time_constant=36000.0)
    for _ in range(100):
        sb.step(step_inputs(P_avail=0.0, P_signal=0.0))
    assert sb.SOC == pytest.approx(0.5 * np.exp(-100 * 60.0 / 36000.0))


def test_SB_discharge_duration_with_degraded_soc_window():
    # A 0.1-0.9 SOC window delivers 80% of energy_capacity: 0.8 * 4 h = 3.2 h at 1 MW
    sb = make_simple_battery(
        dt=60.0,
        energy_capacity=4000.0,
        charge_rate=1000.0,
        discharge_rate=1000.0,
        roundtrip_efficiency=0.9,
        min_SOC=0.1,
        max_SOC=0.9,
        initial_conditions={"SOC": 0.9},
    )
    powers = [
        sb.step(step_inputs(P_avail=0.0, P_signal=-1000.0))["battery"]["power"] for _ in range(250)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(3.2)
    assert sb.SOC == pytest.approx(0.1)
