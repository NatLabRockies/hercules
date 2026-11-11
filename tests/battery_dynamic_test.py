import copy

import numpy as np
import pytest
from hercules.plant_components.battery_dynamic import BatteryDynamic
from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from numpy.testing import assert_almost_equal, assert_array_almost_equal

from tests.test_inputs.h_dict import h_dict_lib_battery, h_dict_simple_battery


def create_simple_battery():
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    return BatteryDynamic(test_h_dict, "battery")


def create_LIB():
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    return BatteryLithiumIon(test_h_dict, "battery")


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
    SB = BatteryDynamic(test_h_dict, "battery")

    assert SB.dt == test_h_dict["dt"]
    assert SB.SOC == test_h_dict["battery"]["initial_conditions"]["SOC"]
    assert SB.SOC_min == 0.0
    assert SB.SOC_max == 1.0
    assert SB.power_min == -2000
    assert SB.power_max == 2000
    assert SB.power_max > SB.power_min
    assert SB.energy_capacity == test_h_dict["battery"]["energy_capacity"]
    assert SB.efficiency_charge == 1
    assert SB.efficiency_discharge == 1
    assert SB.time_constant_self_discharge == np.inf
    assert SB.power_charge == 0
    assert SB.power_reject_charge == 0
    assert SB.power_charge == 0

    # Roundtrip efficiency is applied entirely on charging
    test_h_dict2 = copy.deepcopy(test_h_dict)
    test_h_dict2["battery"]["efficiency_roundtrip"] = 0.9
    test_h_dict2["battery"]["time_constant_self_discharge"] = 100
    SB = BatteryDynamic(test_h_dict2, "battery")
    assert SB.efficiency_charge == 0.9
    assert SB.efficiency_discharge == 1
    assert SB.time_constant_self_discharge == 100


def test_SB_removed_usage_keys_raise():
    # Removed usage-tracking inputs fail loudly rather than being silently ignored
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["track_usage"] = True
    with pytest.raises(ValueError, match="track_usage"):
        BatteryDynamic(test_h_dict, "battery")


def test_SB_control_power_constraint(SB: BatteryDynamic):
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["power_reject"] == 0.5e3
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-2.5e3))
    assert out["battery"]["power"] == -2e3
    assert out["battery"]["power_reject"] == -0.5e3
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 0.25e3
    assert out["battery"]["power_reject"] == 0.75e3


def test_SB_control_energy_constraint(SB: BatteryDynamic):
    SB.energy_kJ = SB.energy_min_kJ + 500
    SB.x[0, 0] = SB.energy_kJ
    out = SB.step(step_inputs(P_avail=3e3, P_signal=-1.5e3))
    assert out["battery"]["power"] == -500
    assert out["battery"]["power_reject"] == -1000
    SB.energy_kJ = SB.energy_max_kJ - 500
    SB.x[0, 0] = SB.energy_kJ
    out = SB.step(step_inputs(P_avail=3e3, P_signal=1.5e3))
    assert out["battery"]["power"] == 500
    assert out["battery"]["power_reject"] == 1000


def test_SB_step(SB: BatteryDynamic):
    SB.step(step_inputs(P_avail=1e3, P_signal=1e3))
    assert_almost_equal(SB.energy_kJ, 144001000, decimal=-2)
    assert_almost_equal(SB.energy, 40000.277, decimal=1)
    assert_almost_equal(SB.SOC, 0.50000347, decimal=6)
    assert SB.power_charge == 1e3
    SB.energy_kJ = SB.energy_min_kJ + 5e3
    SB.x[0, 0] = SB.energy_kJ
    for i in range(4):
        SB.step(step_inputs(P_avail=1e3, P_signal=-2e3))
    assert SB.energy_kJ == 0
    assert SB.energy == 0
    assert SB.SOC == 0
    assert SB.power_charge == 0


def test_SB_small_charge_is_stored():
    # A 2 kW charge on an 80 MWh battery must still accumulate energy (no float32 rounding)
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["efficiency_roundtrip"] = 0.9
    SB = BatteryDynamic(test_h_dict, "battery")
    E0 = SB.x[0, 0]
    for _ in range(10):
        SB.step(step_inputs(P_avail=1e6, P_signal=2.0))
    assert_almost_equal(SB.x[0, 0] - E0, 10 * 2.0 * 0.9 * test_h_dict["dt"], decimal=6)


def test_LI_init():
    """Test init"""
    test_h_dict = copy.deepcopy(h_dict_lib_battery)
    LI = BatteryLithiumIon(test_h_dict, "battery")
    assert LI.dt == test_h_dict["dt"]
    assert LI.SOC == test_h_dict["battery"]["initial_conditions"]["SOC"]
    assert LI.SOC_min == test_h_dict["battery"]["SOC_min"]
    assert LI.SOC_max == test_h_dict["battery"]["SOC_max"]
    assert_almost_equal(LI.power_min, -2000, 6)
    assert_almost_equal(LI.power_max, 2000, 6)
    assert LI.power_max > LI.power_min
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

    assert np.abs(out1["battery"]["power_reject"]) >= np.abs(out2["battery"]["power_reject"])


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


def test_allow_grid_power_consumption(SB: BatteryDynamic):
    # Test with allow_grid_power_consumption = True
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    SB = BatteryDynamic(test_h_dict, "battery")

    # Ask exceeds rated power
    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["power_reject"] == 0.5e3

    test_h_dict["battery"]["allow_grid_power_consumption"] = False
    SB = BatteryDynamic(test_h_dict, "battery")

    out = SB.step(step_inputs(P_avail=3e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 2e3
    assert out["battery"]["power_reject"] == 0.5e3

    out = SB.step(step_inputs(P_avail=1e3, P_signal=2.5e3))
    assert out["battery"]["power"] == 1e3
    assert out["battery"]["power_reject"] == 1.5e3

    # Ask is under rated power
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    SB = BatteryDynamic(test_h_dict, "battery")
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 1e3  # Ignores P_avail, as expected
    assert out["battery"]["power_reject"] == 0

    test_h_dict["battery"]["allow_grid_power_consumption"] = False
    SB = BatteryDynamic(test_h_dict, "battery")
    out = SB.step(step_inputs(P_avail=0.25e3, P_signal=1e3))
    assert out["battery"]["power"] == 0.25e3  # Uses P_avail
    assert out["battery"]["power_reject"] == 0.75e3  # "Rejects" the rest of the signal ask


def test_SB_charge_and_discharge_time():
    # Full discharge lasts energy_capacity / power_discharge_max = 4 h; full charge lasts
    # energy_capacity / (efficiency_roundtrip * power_charge_max) = 4000 / (0.8 * 500) = 10 h
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["dt"] = 60.0
    test_h_dict["battery"]["energy_capacity"] = 4000.0
    test_h_dict["battery"]["power_charge_max"] = 500.0
    test_h_dict["battery"]["power_discharge_max"] = 1000.0
    test_h_dict["battery"]["efficiency_roundtrip"] = 0.8

    test_h_dict["battery"]["initial_conditions"] = {"SOC": 1.0}
    SB = BatteryDynamic(copy.deepcopy(test_h_dict), "battery")
    powers = [
        SB.step(step_inputs(P_avail=0.0, P_signal=-1000.0))["battery"]["power"] for _ in range(300)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(4.0)
    assert SB.SOC == pytest.approx(0.0, abs=1e-9)

    test_h_dict["battery"]["initial_conditions"] = {"SOC": 0.0}
    SB = BatteryDynamic(copy.deepcopy(test_h_dict), "battery")
    powers = [
        SB.step(step_inputs(P_avail=1e6, P_signal=500.0))["battery"]["power"] for _ in range(700)
    ]
    assert sum(abs(p) > 1e-6 for p in powers) * 60.0 / 3600 == pytest.approx(10.0)
    assert SB.SOC == pytest.approx(1.0)


def test_SB_roundtrip_efficiency():
    """Test round-trip efficiency for BatteryDynamic.

    Tests that a complete charge-discharge cycle returns the expected
    amount of energy based on the specified round-trip efficiency.
    """
    # Test with 90% round-trip efficiency
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["efficiency_roundtrip"] = 0.9
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
    SB = BatteryDynamic(test_h_dict, "battery")

    # Roundtrip efficiency is applied entirely on charging
    assert_almost_equal(SB.efficiency_charge, 0.9, 6)
    assert_almost_equal(SB.efficiency_discharge, 1.0, 6)
    assert_almost_equal(SB.efficiency_charge * SB.efficiency_discharge, 0.9, 6)

    # Record initial state
    initial_energy = SB.energy

    # Use a smaller test that won't hit SOC limits
    # Charge with 500 kW for 30 minutes (250 kWh input)
    charge_power = 500  # kW
    charge_time_steps = int(1800 / SB.dt)  # 30 minutes worth of time steps

    for _ in range(charge_time_steps):
        SB.step(step_inputs(P_avail=charge_power, P_signal=charge_power))

    # Record state after charging
    charged_energy = SB.energy
    energy_stored = charged_energy - initial_energy

    # Expected stored energy should be charge_power * 0.5hr * eta_charge
    expected_stored = charge_power * 0.5 * SB.efficiency_charge  # 250 * 0.9
    assert_almost_equal(energy_stored, expected_stored, 1)

    # Now discharge the battery with the same power magnitude for the same time
    discharge_power = -charge_power  # kW (negative for discharge)

    for _ in range(charge_time_steps):
        SB.step(step_inputs(P_avail=0, P_signal=discharge_power))

    # Record final state
    final_energy = SB.energy

    # Calculate net energy change
    net_energy_change = final_energy - initial_energy

    # For a complete round trip, we should have lost energy due to efficiency
    # Net loss = input_energy * (1 - efficiency_roundtrip)
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
    """Test that BatteryDynamic with perfect efficiency (1.0) has no losses."""
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["efficiency_roundtrip"] = 1.0
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
    SB = BatteryDynamic(test_h_dict, "battery")

    # Verify perfect efficiency
    assert SB.efficiency_charge == 1.0
    assert SB.efficiency_discharge == 1.0

    # Record initial state
    initial_energy = SB.energy

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
    final_energy = SB.energy
    assert_almost_equal(final_energy, initial_energy, 2)


def test_SB_roundtrip_efficiency_various_values():
    """Test round-trip efficiency with various efficiency values."""
    efficiency_values = [0.7, 0.8, 0.85, 0.9, 0.95]

    for rte in efficiency_values:
        test_h_dict = copy.deepcopy(h_dict_simple_battery)
        test_h_dict["battery"]["efficiency_roundtrip"] = rte
        test_h_dict["battery"]["allow_grid_power_consumption"] = True
        test_h_dict["battery"]["initial_conditions"]["SOC"] = 0.5  # Start at middle SOC
        SB = BatteryDynamic(test_h_dict, "battery")

        # Small charge-discharge cycle to avoid SOC limits
        initial_energy = SB.energy

        charge_power = 200  # kW
        time_steps = int(900 / SB.dt)  # 15 minutes

        # Charge
        for _ in range(time_steps):
            SB.step(step_inputs(P_avail=charge_power, P_signal=charge_power))

        # Discharge
        for _ in range(time_steps):
            SB.step(step_inputs(P_avail=0, P_signal=-charge_power))

        # Verify the round-trip efficiency
        final_energy = SB.energy
        energy_loss = initial_energy - final_energy
        energy_throughput = charge_power * (time_steps * SB.dt / 3600)  # kWh

        expected_loss = energy_throughput * (1 - rte)

        # Allow for numerical integration effects
        relative_error = abs(energy_loss - expected_loss) / expected_loss
        assert relative_error < 0.2, (
            f"RTE={rte}: Actual loss: {energy_loss:.2f} kWh, Expected: {expected_loss:.2f} kWh, "
            f"Relative error: {relative_error:.3f}"
        )


def test_SB_discharge_duration_invariant():
    """Test that discharge duration equals energy_capacity / power_discharge_max regardless of RTE.

    A 4 MWh battery with 1 MW discharge rate should take exactly 4 hours to fully
    discharge, even when roundtrip efficiency < 1. The RTE losses should not reduce
    the deliverable energy duration.
    """
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["energy_capacity"] = 4000  # 4 MWh
    test_h_dict["battery"]["power_charge_max"] = 1000  # 1 MW
    test_h_dict["battery"]["power_discharge_max"] = 1000  # 1 MW
    test_h_dict["battery"]["efficiency_roundtrip"] = 0.9
    test_h_dict["battery"]["SOC_max"] = 1.0
    test_h_dict["battery"]["SOC_min"] = 0.0
    test_h_dict["battery"]["initial_conditions"] = {"SOC": 1.0}
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["dt"] = 1.0

    SB = BatteryDynamic(test_h_dict, "battery")

    # Discharge at full rated power and count how many steps until empty
    expected_steps = 14400  # 4 hours * 3600 s/hr / 1 s/step
    steps_taken = 0
    for i in range(expected_steps + 1000):  # Run extra to find when it empties
        SB.step(step_inputs(P_avail=0, P_signal=-1000))
        steps_taken += 1
        if SB.SOC <= 0.0:
            break

    # The battery should discharge in exactly 4 hours (14400 steps), not sooner
    assert abs(steps_taken - expected_steps) <= 1, (
        f"Battery should take {expected_steps} steps (4 hours) to fully discharge "
        f"at 1 MW from 4 MWh with RTE=0.9, but took {steps_taken} steps "
        f"({steps_taken / 3600:.3f} hours)."
    )


def test_SB_discharge_duration_with_degraded_soc_window():
    """Test that non-default SOC limits reduce deliverable duration proportionally.

    SOC_min and SOC_max represent deviations from nameplate performance (e.g.,
    degradation). When the usable SOC window is less than 0-1, the deliverable
    energy and thus discharge duration are reduced proportionally.
    """
    test_h_dict = copy.deepcopy(h_dict_simple_battery)
    test_h_dict["battery"]["energy_capacity"] = 4000  # 4 MWh
    test_h_dict["battery"]["power_charge_max"] = 1000  # 1 MW
    test_h_dict["battery"]["power_discharge_max"] = 1000  # 1 MW
    test_h_dict["battery"]["efficiency_roundtrip"] = 0.9
    test_h_dict["battery"]["SOC_max"] = 0.9  # degraded: can only use 80% of capacity
    test_h_dict["battery"]["SOC_min"] = 0.1
    test_h_dict["battery"]["initial_conditions"] = {"SOC": 0.9}
    test_h_dict["battery"]["allow_grid_power_consumption"] = True
    test_h_dict["dt"] = 1.0

    SB = BatteryDynamic(test_h_dict, "battery")

    # With SOC window of 0.8 (0.1 to 0.9), deliverable duration should be
    # 0.8 * energy_capacity / power_discharge_max = 0.8 * 4 hours = 3.2 hours
    expected_steps = int(0.8 * 14400)  # 11520 steps
    steps_taken = 0
    for i in range(expected_steps + 1000):
        SB.step(step_inputs(P_avail=0, P_signal=-1000))
        steps_taken += 1
        if SB.SOC <= SB.SOC_min:
            break

    assert abs(steps_taken - expected_steps) <= 1, (
        f"Degraded battery (SOC 0.1-0.9) should take {expected_steps} steps "
        f"(3.2 hours) to fully discharge at 1 MW from 4 MWh, but took "
        f"{steps_taken} steps ({steps_taken / 3600:.3f} hours)."
    )
