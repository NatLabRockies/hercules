"""Regression tests for 'SolarPySAM'."""

import copy

import numpy as np
from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
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

usage_calc_base_dict = {
    "out_power": 1800,
    "SB.total_cycle_usage": 0.02193261935938851,
    "SB.cycle_usage_perc": 0.43865238718777017,
    "SB.total_time_usage": 20.0,
    "SB.time_usage_perc": 63.41958396752917,
    "SB.SOC (1)": 0.18644728149025358,
    "SB.SOC (2)": 0.15097155977675195,
}


def test_SimpleBattery_regression_():
    battery = BatterySimple(test_h_dict)

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


def test_LIB_regression_():
    battery = BatteryLithiumIon(test_h_dict)

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


def test_SimpleBattery_usage_calc_regression():
    battery_dict = copy.deepcopy(test_h_dict)
    battery_dict["dt"] = 1

    # Modify battery configuration for testing
    battery_dict["battery"]["size"] = 2000
    battery_dict["battery"]["energy_capacity"] = 8000
    battery_dict["battery"]["charge_rate"] = 2000
    battery_dict["battery"]["discharge_rate"] = 2000
    battery_dict["battery"]["roundtrip_efficiency"] = 0.9
    battery_dict["battery"]["self_discharge_time_constant"] = 100
    battery_dict["battery"]["track_usage"] = True
    battery_dict["battery"]["usage_calc_interval"] = 10
    battery_dict["battery"]["usage_lifetime"] = 0.000001
    battery_dict["battery"]["usage_cycles"] = 5
    battery_dict["battery"]["initial_conditions"] = {"SOC": 0.23}

    SB = BatterySimple(battery_dict)

    power_avail = 10e3 * np.ones(21)
    power_signal = [
        1500,
        1500,
        1500,
        -1700,
        -1700,
        -1700,
        1800,
        1800,
        1800,
        1800,
        1800,
        -1800,
        -1800,
        -1800,
        -1800,
        -1800,
        1800,
        1800,
        1800,
        1800,
        1800,
    ]

    for i in range(len(power_avail)):
        step_input_dict = {
            "battery": {"power_setpoint": power_signal[i]},
            "plant": {"locally_generated_power": power_avail[i]},
        }
        out = SB.step(step_input_dict)
        # assert out["battery"]["power"] == power_signal[i]

    assert SB.step_counter == 1
    assert out["battery"]["power"] == usage_calc_base_dict["out_power"]

    assert SB.total_cycle_usage == usage_calc_base_dict["SB.total_cycle_usage"]
    assert_almost_equal(SB.cycle_usage_perc, usage_calc_base_dict["SB.cycle_usage_perc"], decimal=4)
    assert SB.total_time_usage == usage_calc_base_dict["SB.total_time_usage"]
    assert SB.time_usage_perc == usage_calc_base_dict["SB.time_usage_perc"]

    assert_almost_equal(SB.SOC, usage_calc_base_dict["SB.SOC (1)"], decimal=4)

    if PRINT_VALUES:
        print("out_power: ", out["battery"]["power"])
        print("SB.total_cycle_usage: ", SB.total_cycle_usage)
        print("SB.cycle_usage_perc: ", SB.cycle_usage_perc)
        print("SB.total_time_usage: ", SB.total_time_usage)
        print("SB.time_usage_perc: ", SB.time_usage_perc)
        print("SB.SOC (1): ", SB.SOC)

    for i in range(len(power_avail)):
        step_input_dict = {
            "battery": {"power_setpoint": 0},
            "plant": {"locally_generated_power": power_avail[i]},
        }
        out = SB.step(step_input_dict)
    assert_almost_equal(SB.SOC, usage_calc_base_dict["SB.SOC (2)"], decimal=4)

    if PRINT_VALUES:
        print("SB.SOC (2): ", SB.SOC)
