import numpy as np
import pytest
from hercules.python_simulators.battery import LIB, SimpleBattery
from numpy.testing import assert_almost_equal, assert_array_almost_equal


def get_battery_params(battery_type):
    battery_dict = {
        "py_sim_type": battery_type,
        "size": 20,  # MW size of the battery
        "energy_capacity": 80,  # total capcity of the battery in MWh (4-hour 20 MW battery)
        "charge_rate": 2,  # charge rate of the battery in MW
        "discharge_rate": 2,  # discharge rate of the battery in MW
        "max_SOC": 0.9,  # upper boundary on battery SOC
        "min_SOC": 0.1,  # lower boundary on battery SOC
        "initial_conditions": {"SOC": 0.102},
    }
    dt = 1
    return battery_dict, dt


def create_simple_battery():
    battery_dict, dt = get_battery_params(SimpleBattery)
    return SimpleBattery(battery_dict, dt)


def create_LIB():
    battery_dict, dt = get_battery_params(LIB)
    return LIB(battery_dict, dt)


@pytest.fixture
def SB():
    return create_simple_battery()


@pytest.fixture
def LI():
    return create_LIB()


def step_inputs(P_avail, P_signal):
    return dict(
        {
            "py_sims": {"inputs": {"locally_generated_power": P_avail, "battery_signal": P_signal}},
        }
    )


def test_SB_init():
    battery_dict, dt = get_battery_params(SimpleBattery)
    SB = SimpleBattery(battery_dict, dt)

    assert SB.dt == dt

    assert SB.SOC == battery_dict["initial_conditions"]["SOC"]
    assert SB.SOC_min == battery_dict["min_SOC"]
    assert SB.SOC_max == battery_dict["max_SOC"]

    assert SB.P_min == -2000
    assert SB.P_max == 2000
    assert SB.P_max > SB.P_min

    assert SB.energy_capacity == battery_dict["energy_capacity"] * 1e3

    assert SB.eta_charge == 1
    assert SB.eta_discharge == 1

    assert SB.tau_self_discharge == np.inf

    assert not SB.track_usage
    assert SB.usage_calc_interval == np.inf

    assert SB.power_kw == 0
    assert SB.P_reject == 0
    assert SB.P_charge == 0

    battery_dict["roundtrip_efficiency"] = 0.9
    battery_dict["self_discharge_time_constant"] = 100
    battery_dict["track_usage"] = True
    battery_dict["usage_calc_interval"] = 100
    battery_dict["usage_lifetime"] = 0.1
    battery_dict["usage_cycles"] = 10

    SB = SimpleBattery(battery_dict, dt)

    assert SB.eta_charge == np.sqrt(0.9)
    assert SB.eta_discharge == np.sqrt(0.9)

    assert SB.tau_self_discharge == 100

    assert SB.track_usage
    assert SB.usage_calc_interval == 100
    assert SB.usage_time_rate == 3.170979198376459e-7
    assert SB.usage_cycles_rate == 0.1

def test_SB_return_outputs(SB: SimpleBattery):
    # outputs after initialization - all outputs should reflect input dict
    outputs_init = SB.return_outputs()

    assert outputs_init["power"] == 0
    assert outputs_init["reject"] == 0
    assert outputs_init["soc"] == 0.102
    assert outputs_init["usage_in_time"] == 0
    assert outputs_init["usage_in_cycles"] == 0
    assert outputs_init["total_cycles"] == 0

    # change simple battery state as if during simulation
    SB.power_kw = 35000
    SB.P_reject = 2
    SB.SOC = 0.25
    SB.time_usage_perc = 23
    SB.cycle_usage_perc = 25
    SB.total_cycle_usage = 143

    # check that outputs return the changed battery state
    outputs_sim = SB.return_outputs()

    assert outputs_sim["power"] == 35000
    assert outputs_sim["reject"] == 2
    assert outputs_sim["soc"] == 0.25
    assert outputs_sim["usage_in_time"] == 23
    assert outputs_sim["usage_in_cycles"] == 25
    assert outputs_sim["total_cycles"] == 143

def test_SB_control_power_constraint(SB: SimpleBattery):
    # test upper charging limit
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["power"] == 2e3
    assert out["reject"] == 0.5e3

    # Test lower charging limit
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-2.5e3))
    assert out["power"] == -2e3
    assert out["reject"] == -0.5e3

    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["power"] == 0.25e3
    assert out["reject"] == 0.75e3


def test_SB_control_energy_constraint(SB: SimpleBattery):
    SB.E = SB.E_min + 500
    SB.x[0,0] = SB.E
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-1.5e3))
    assert out["power"] == -500
    assert out["reject"] == -1000

    SB.E = SB.E_max - 500
    SB.x[0,0] = SB.E
    out = SB.step(step_inputs(P_avail=3e3, P_signal=1.5e3))
    assert out["power"] == 500
    assert out["reject"] == 1000


def test_SB_step(SB: SimpleBattery):
    SB.step(step_inputs(P_avail=1e3, P_signal=1e3))

    assert_almost_equal(SB.E, 29377000, decimal=6)
    assert_almost_equal(SB.current_batt_state, 8160.27, decimal=1)
    assert_almost_equal(SB.SOC, 0.102003472, decimal=8)
    assert SB.P_charge == 1e3

    SB.E = SB.E_min + 5e3
    SB.x[0,0] = SB.E


    for i in range(4):
        SB.step(step_inputs(P_avail=1e3, P_signal=-2e3))

    assert SB.E == 28800000
    assert SB.current_batt_state == 8000
    assert SB.SOC == 0.1
    assert SB.P_charge == 0


def test_LI_init():
    """Test init"""

    battery_dict, dt = get_battery_params(LIB)
    LI = LIB(battery_dict, dt)

    assert LI.dt == dt

    assert LI.SOC == battery_dict["initial_conditions"]["SOC"]
    assert LI.SOC_min == battery_dict["min_SOC"]
    assert LI.SOC_max == battery_dict["max_SOC"]

    assert_almost_equal(LI.P_min, -2000, 6)
    assert_almost_equal(LI.P_max, 2000, 6)
    assert LI.P_max > LI.P_min

    assert LI.energy_capacity == battery_dict["energy_capacity"] * 1e3


def test_LI_post_init():
    battery_dict, dt = get_battery_params(LIB)
    LI = LIB(battery_dict, dt)

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

    assert_almost_equal(out["power"], P_signal, 0)
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

    assert np.abs(out1["reject"]) >= np.abs(out2["reject"])


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

def test_allow_grid_power_consumption(SB: SimpleBattery):
    # Test with allow_grid_power_consumption = True
    battery_dict, dt = get_battery_params(SimpleBattery)
    battery_dict["allow_grid_power_consumption"] = True
    SB = SimpleBattery(battery_dict, dt)

    # Ask exceeds rated power
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["power"] == 2e3
    assert out["reject"] == 0.5e3

    battery_dict["allow_grid_power_consumption"] = False
    SB = SimpleBattery(battery_dict, dt)

    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["power"] == 2e3
    assert out["reject"] == 0.5e3

    out = SB.step(step_inputs(P_avail=1e3, P_signal=2.5e3))
    assert out["power"] == 1e3
    assert out["reject"] == 1.5e3

    # Ask is under rated power
    battery_dict["allow_grid_power_consumption"] = True
    SB = SimpleBattery(battery_dict, dt)
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["power"] == 1e3 # Ignores P_avail, as expected
    assert out["reject"] == 0

    battery_dict["allow_grid_power_consumption"] = False
    SB = SimpleBattery(battery_dict, dt)
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["power"] == 0.25e3 # Uses P_avail
    assert out["reject"] == 0.75e3 # "Rejects" the rest of the signal ask
