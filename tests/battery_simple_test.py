import copy

import numpy as np
import pytest
from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from numpy.testing import assert_almost_equal, assert_array_almost_equal

from tests.test_inputs.h_dict import h_dict_lib_battery, h_dict_simple_battery


def create_simple_battery():
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    return BatterySimple(test_h_dict)


def create_LIB():
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    return BatteryLithiumIon(test_h_dict)


@pytest.fixture
def SB():
    return create_simple_battery()


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
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    SB = BatterySimple(test_h_dict)

    assert SB.dt == test_h_dict["dt"]
    assert SB.SOC == test_h_dict["battery"]["initial_conditions"]["SOC"]
    assert SB.SOC_min == test_h_dict["battery"]["min_SOC"]
    assert SB.SOC_max == test_h_dict["battery"]["max_SOC"]
    assert SB.P_min == -2000
    assert SB.P_max == 2000
    assert SB.P_max > SB.P_min
    assert SB.energy_capacity == test_h_dict["battery"]["energy_capacity"]
    assert SB.eta_charge == 1
    assert SB.eta_discharge == 1
    assert SB.tau_self_discharge == np.inf
    assert not SB.track_usage
    assert SB.usage_calc_interval == np.inf
    assert SB.power_kw == 0
    assert SB.P_reject == 0
    assert SB.P_charge == 0

    # Test with additional parameters
    test_h_dict2 = copy.deepcopy(test_h_dict)
    test_h_dict2["battery"]["roundtrip_efficiency"] = 0.9
    test_h_dict2["battery"]["self_discharge_time_constant"] = 100
    test_h_dict2["battery"]["track_usage"] = True
    test_h_dict2["battery"]["usage_calc_interval"] = 100
    test_h_dict2["battery"]["usage_lifetime"] = 0.1
    test_h_dict2["battery"]["usage_cycles"] = 10
    SB = BatterySimple(test_h_dict2)
    assert SB.eta_charge == np.sqrt(0.9)
    assert SB.eta_discharge == np.sqrt(0.9)
    assert SB.tau_self_discharge == 100
    assert SB.track_usage
    assert SB.usage_calc_interval == 100 / test_h_dict2["dt"]
    assert SB.usage_time_rate == 1 / (0.1 * 365 * 24 * 3600 / test_h_dict2["dt"])
    assert SB.usage_cycles_rate == 1 / 10


def test_SB_control_power_constraint(SB: BatterySimple):
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["reject"] == 0.5e3
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-2.5e3))
    assert out["battery"]["power"] == -2e3
    assert out["battery"]["reject"] == -0.5e3
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 0.25e3
    assert out["battery"]["reject"] == 0.75e3


def test_SB_control_energy_constraint(SB: BatterySimple):
    SB.E = SB.E_min + 500
    SB.x[0, 0] = SB.E
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-1.5e3))
    assert out["battery"]["power"] == -500
    assert out["battery"]["reject"] == -1000
    SB.E = SB.E_max - 500
    SB.x[0, 0] = SB.E
    out = SB.step(step_inputs(P_avail=3e3, P_signal=1.5e3))
    assert out["battery"]["power"] == 500
    assert out["battery"]["reject"] == 1000


def test_SB_step(SB: BatterySimple):
    SB.step(step_inputs(P_avail=1e3, P_signal=1e3))
    assert_almost_equal(SB.E, 29377000, decimal=6)
    assert_almost_equal(SB.current_batt_state, 8160.27, decimal=1)
    assert_almost_equal(SB.SOC, 0.102003472, decimal=8)
    assert SB.P_charge == 1e3
    SB.E = SB.E_min + 5e3
    SB.x[0, 0] = SB.E
    for i in range(4):
        SB.step(step_inputs(P_avail=1e3, P_signal=-2e3))
    assert SB.E == 28800000
    assert SB.current_batt_state == 8000
    assert SB.SOC == 0.1
    assert SB.P_charge == 0


def test_LI_init():
    """Test init"""
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    LI = BatteryLithiumIon(test_h_dict)
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
    LI = BatteryLithiumIon(test_h_dict)
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
    assert LI.OCV() == 3.2654698427383457

    LI.SOC = 0.75
    assert LI.OCV() == 3.316731143986497


def test_LI_build_SS(LI):
    """Check ABCD matrices for different conditions"""

    assert_array_almost_equal(
        LI.build_SS(),
        [-0.017767729688006585, 1, 7.533462876320113e-05, 0.002720095833999999],
        12,
    )

    LI.SOC = 0.75
    LI.SOH = 0.75
    LI.T = 10
    assert_array_almost_equal(
        LI.build_SS(),
        [-0.026421742559794213, 1, 0.00012815793568836145, 0.00555564775],
        12,
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
        9,
    )


def test_LI_calc_power(LI):
    assert LI.calc_power(400) == 1593832.1960216616

    LI.SOC = 0.75
    assert LI.calc_power(400) == 1645641.7527372995

    LI.step_cell(10)
    assert LI.calc_power(400) == 1658686.3702462215


def test_LI_step(LI):
    P_avail = 1.5e3
    P_signal = 1e3

    out = LI.step(step_inputs(P_avail=P_avail, P_signal=P_signal))

    assert_almost_equal(out["battery"]["power"], P_signal, 0)
    assert LI.SOC == 0.10200356700632712
    assert LI.V_RC == 0.0005503468409411925


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


def test_allow_grid_power_consumption(SB: BatterySimple):
    # Test with allow_grid_power_consumption = True
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    SB = BatterySimple(test_h_dict)

    # Ask exceeds rated power
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["reject"] == 0.5e3

    test_h_dict["battery"]["allow_grid_power_consumption"] = False
    SB = BatterySimple(test_h_dict)

    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["reject"] == 0.5e3

    out = SB.step(step_inputs(P_avail=1e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 1e3
    assert out["battery"]["reject"] == 1.5e3

    # Ask is under rated power
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    SB = BatterySimple(test_h_dict)
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 1e3  # Ignores P_avail, as expected
    assert out["battery"]["reject"] == 0

    test_h_dict["battery"]["allow_grid_power_consumption"] = False
    SB = BatterySimple(test_h_dict)
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 0.25e3  # Uses P_avail
    assert out["battery"]["reject"] == 0.75e3  # "Rejects" the rest of the signal ask
