"""Regression tests for battery models."""

import copy

import numpy as np
from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_reservoir import BatteryReservoir
from hercules.plant_components.battery_simple import BatterySimple
from numpy.testing import assert_almost_equal

PRINT_VALUES = True

test_h_dict = {
    "dt": 0.5,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "battery": {
        "size": 20000,  # kW size of the battery (20 MW)
        "energy_capacity": 80000,  # total capacity of the battery in kWh (80 MWh)
        "charge_rate": 20000,  # charge rate in kW (20 MW)
        "discharge_rate": 20000,  # discharge rate in kW (20 MW)
        "max_SOC": 0.9,
        "min_SOC": 0.1,
        "initial_conditions": {"SOC": 0.5},
    },
}

np.random.seed(0)
powers_requested = np.concatenate(
    (
        np.linspace(0, 100000, 3),  # Ramp up
        np.linspace(100000, -5000, 6),  # Ramp down
        np.random.normal(-500, 100, 3),  # Random fluctuations
    )
)

powers_base_simple = np.array(
    [
        0.0,
        20000.0,
        20000.0,
        20000.0,
        20000.0,
        20000.0,
        20000.0,
        16000.0,
        -5000.0,
        -323.5947654,
        -459.98427916,
    ]
)

reject_base_simple = np.array(
    [0.0, 30000.0, 80000.0, 80000.0, 59000.0, 38000.0, 17000.0, 0.0, 0.0, 0.0, 0.0]
)

soc_base_simple = np.array(
    [
        0.5,
        0.50003472,
        0.50006944,
        0.50010417,
        0.50013889,
        0.50017361,
        0.50020833,
        0.50023611,
        0.50022743,
        0.50022687,
        0.50022607,
    ]
)

powers_base_lib = np.array(
    [
        0.0,
        20047.11229812,
        20047.95046608,
        20048.77886147,
        20049.59760268,
        20050.40680666,
        20051.20658894,
        15990.37116823,
        -4983.52093018,
        -323.83088639,
        -459.97259284,
    ]
)

reject_base_lib = np.array(
    [
        0.00000000e00,
        2.99528877e04,
        7.99520495e04,
        7.99512211e04,
        5.89504024e04,
        3.79495932e04,
        1.69487934e04,
        9.62883177e00,
        -1.64790698e01,
        2.36120986e-01,
        -1.16863220e-02,
    ]
)

soc_base_lib = np.array(
    [
        0.5,
        0.50003472,
        0.50006944,
        0.50010417,
        0.50013889,
        0.50017361,
        0.50020833,
        0.50023604,
        0.50022738,
        0.50022681,
        0.50022601,
    ]
)

# Baselines from the pre-refactor model (RTE split as sqrt on charge and discharge)
rte_self_discharge_base_dict = {
    "out_power": 1800,
    "SB.SOC (1)": 0.18643651054788266,
    "SB.SOC (2)": 0.15096283896030407,
}


def test_SimpleBattery_regression_():
    battery = BatterySimple(test_h_dict, "battery")

    times_test = np.arange(0, 5.5, test_h_dict["dt"])
    powers_test = np.zeros_like(times_test)
    reject_test = np.zeros_like(times_test)
    soc_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = battery.step(
            {
                "time": t,
                "battery": {
                    "power_setpoint": powers_requested[i],
                },
                "plant": {"locally_generated_power": powers_requested[i]},
            }
        )
        powers_test[i] = out["battery"]["power"]
        reject_test[i] = out["battery"]["reject"]
        soc_test[i] = out["battery"]["soc"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("Rejected: ", reject_test)
        print("SOC: ", soc_test)

    assert np.allclose(powers_base_simple, powers_test)
    assert np.allclose(reject_base_simple, reject_test)
    assert np.allclose(soc_base_simple, soc_test)


def test_BatteryReservoir_regression_():
    battery = BatteryReservoir(test_h_dict, "battery")

    times_test = np.arange(0, 5.5, test_h_dict["dt"])
    powers_test = np.zeros_like(times_test)
    soc_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = battery.step(
            {
                "time": t,
                "battery": {
                    "power_setpoint": powers_requested[i],
                },
                "plant": {"locally_generated_power": powers_requested[i]},
            }
        )
        powers_test[i] = out["battery"]["power"]
        soc_test[i] = out["battery"]["soc"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("SOC: ", soc_test)

    # Identical to BatterySimple at unit efficiency without self-discharge
    assert np.allclose(powers_base_simple, powers_test)
    assert np.allclose(soc_base_simple, soc_test)


def test_LIB_regression_():
    battery = BatteryLithiumIon(test_h_dict, "battery")

    times_test = np.arange(0, 5.5, test_h_dict["dt"])
    powers_test = np.zeros_like(times_test)
    reject_test = np.zeros_like(times_test)
    soc_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = battery.step(
            {
                "time": t,
                "battery": {
                    "power_setpoint": powers_requested[i],
                },
                "plant": {"locally_generated_power": powers_requested[i]},
            }
        )
        powers_test[i] = out["battery"]["power"]
        reject_test[i] = out["battery"]["reject"]
        soc_test[i] = out["battery"]["soc"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("Rejected: ", reject_test)
        print("SOC: ", soc_test)

    assert np.allclose(powers_base_lib, powers_test)
    assert np.allclose(reject_base_lib, reject_test)
    assert np.allclose(soc_base_lib, soc_test)


def test_SimpleBattery_rte_self_discharge_regression():
    # Charge-only RTE must reproduce the pre-refactor SOC with RTE and self-discharge
    battery_dict = copy.deepcopy(test_h_dict)
    battery_dict["dt"] = 1
    battery_dict["battery"]["energy_capacity"] = 8000
    battery_dict["battery"]["charge_rate"] = 2000
    battery_dict["battery"]["discharge_rate"] = 2000
    battery_dict["battery"]["roundtrip_efficiency"] = 0.9
    battery_dict["battery"]["self_discharge_time_constant"] = 100
    battery_dict["battery"]["initial_conditions"] = {"SOC": 0.23}

    SB = BatterySimple(battery_dict, "battery")

    power_signal = [1500] * 3 + [-1700] * 3 + [1800] * 5 + [-1800] * 5 + [1800] * 5
    for setpoint in power_signal:
        out = SB.step(
            {
                "battery": {"power_setpoint": setpoint},
                "plant": {"locally_generated_power": 10e3},
            }
        )

    assert out["battery"]["power"] == rte_self_discharge_base_dict["out_power"]
    assert_almost_equal(SB.SOC, rte_self_discharge_base_dict["SB.SOC (1)"], decimal=4)

    for _ in range(len(power_signal)):
        SB.step({"battery": {"power_setpoint": 0}, "plant": {"locally_generated_power": 10e3}})
    assert_almost_equal(SB.SOC, rte_self_discharge_base_dict["SB.SOC (2)"], decimal=4)

    if PRINT_VALUES:
        print("SB.SOC (2): ", SB.SOC)
