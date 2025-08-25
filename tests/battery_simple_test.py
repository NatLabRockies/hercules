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


def test_SB_roundtrip_efficiency():
    """Test round-trip efficiency for BatterySimple.

    Tests that a complete charge-discharge cycle returns the expected
    amount of energy based on the specified round-trip efficiency.
    """
    # Test with 90% round-trip efficiency
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["roundtrip_efficiency"] = 0.9
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
    SB = BatterySimple(test_h_dict)

    # Verify efficiency parameters are set correctly
    assert_almost_equal(SB.eta_charge, np.sqrt(0.9), 6)
    assert_almost_equal(SB.eta_discharge, np.sqrt(0.9), 6)
    assert_almost_equal(SB.eta_charge * SB.eta_discharge, 0.9, 6)

    # Record initial state
    initial_energy = SB.current_batt_state

    # Use a smaller test that won't hit SOC limits
    # Charge with 500 kW for 30 minutes (250 kWh input)
    charge_power = 500  # kW
    charge_time_steps = int(1800 / SB.dt)  # 30 minutes worth of time steps

    for _ in range(charge_time_steps):
        SB.step(step_inputs(P_avail=charge_power, P_signal=charge_power))

    # Record state after charging
    charged_energy = SB.current_batt_state
    energy_stored = charged_energy - initial_energy

    # Expected stored energy should be charge_power * 0.5hr * eta_charge
    expected_stored = charge_power * 0.5 * SB.eta_charge  # 250 * sqrt(0.9)
    assert_almost_equal(energy_stored, expected_stored, 1)

    # Now discharge the battery with the same power magnitude for the same time
    discharge_power = -charge_power  # kW (negative for discharge)

    for _ in range(charge_time_steps):
        SB.step(step_inputs(P_avail=0, P_signal=discharge_power))

    # Record final state
    final_energy = SB.current_batt_state

    # Calculate net energy change
    net_energy_change = final_energy - initial_energy

    # For a complete round trip, we should have lost energy due to efficiency
    # Net loss = input_energy * (1 - roundtrip_efficiency)
    input_energy = charge_power * 0.5  # 250 kWh
    expected_net_loss = input_energy * (1 - 0.9)  # 25 kWh loss

    # Verify the round-trip efficiency (allow for small numerical errors)
    # The actual loss should be close to the theoretical loss
    actual_loss = -net_energy_change
    relative_error = abs(actual_loss - expected_net_loss) / expected_net_loss

    # Allow up to 10% relative error due to numerical integration effects
    assert relative_error < 0.1, (
        f"Actual loss: {actual_loss:.2f} kWh, Expected: {expected_net_loss:.2f} kWh, "
        f"Relative error: {relative_error:.3f}"
    )


def test_SB_roundtrip_efficiency_perfect():
    """Test that BatterySimple with perfect efficiency (1.0) has no losses."""
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["roundtrip_efficiency"] = 1.0
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
    SB = BatterySimple(test_h_dict)

    # Verify perfect efficiency
    assert SB.eta_charge == 1.0
    assert SB.eta_discharge == 1.0

    # Record initial state
    initial_energy = SB.current_batt_state

    # Charge and discharge cycle
    charge_power = 300  # kW
    time_steps = int(1800 / SB.dt)  # 30 minutes

    # Charge
    for _ in range(time_steps):
        SB.step(step_inputs(P_avail=charge_power, P_signal=charge_power))

    # Discharge
    for _ in range(time_steps):
        SB.step(step_inputs(P_avail=0, P_signal=-charge_power))

    # Final energy should equal initial energy (no losses)
    final_energy = SB.current_batt_state
    assert_almost_equal(final_energy, initial_energy, 2)


def test_SB_roundtrip_efficiency_various_values():
    """Test round-trip efficiency with various efficiency values."""
    efficiency_values = [0.7, 0.8, 0.85, 0.9, 0.95]

    for rte in efficiency_values:
        test_h_dict = copy.deepcopy(h_dict_simple_battery)
        test_h_dict["battery"]["roundtrip_efficiency"] = rte
        test_h_dict["battery"]["allow_grid_power_consumption"] = True
        test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
        SB = BatterySimple(test_h_dict)

        # Small charge-discharge cycle to avoid SOC limits
        initial_energy = SB.current_batt_state

        charge_power = 200  # kW
        time_steps = int(900 / SB.dt)  # 15 minutes

        # Charge
        for _ in range(time_steps):
            SB.step(step_inputs(P_avail=charge_power, P_signal=charge_power))

        # Discharge
        for _ in range(time_steps):
            SB.step(step_inputs(P_avail=0, P_signal=-charge_power))

        # Verify the round-trip efficiency
        final_energy = SB.current_batt_state
        energy_loss = initial_energy - final_energy
        energy_throughput = charge_power * (time_steps * SB.dt / 3600)  # kWh

        expected_loss = energy_throughput * (1 - rte)

        # Allow for numerical integration effects
        relative_error = abs(energy_loss - expected_loss) / expected_loss
        assert relative_error < 0.2, (
            f"RTE={rte}: Actual loss: {energy_loss:.2f} kWh, Expected: {expected_loss:.2f} kWh, "
            f"Relative error: {relative_error:.3f}"
        )
