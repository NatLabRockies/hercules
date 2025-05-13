"""Regression tests for 'SolarPySAM'."""

import numpy as np
from hercules.python_simulators.battery import LIB, SimpleBattery

PRINT_VALUES = True

test_input_dict = {
    "size": 20,
    "energy_capacity": 80,
    "charge_rate": 20,
    "discharge_rate": 20,
    "max_SOC": 0.9,
    "min_SOC": 0.1,
    "initial_conditions": {"SOC": 0.5},
}

np.random.seed(0)
powers_requested = np.concatenate(
    (
        np.linspace(0, 100000, 3), # Ramp up
        np.linspace(100000, -5000, 6), # Ramp down
        np.random.normal(-500, 100, 3) # Random fluctuations
    )
)

powers_base_simple = np.array(
    [
        0.,
        20000.,
        20000.,
        20000.,
        20000.,
        20000.,
        20000.,
        16000.,
        -5000.,
        -323.5947654,
        -459.98427916,
    ]
)

reject_base_simple = np.array(
    [
        0.    ,
        30000.,
        80000.,
        80000.,
        59000.,
        38000.,
        17000.,
        0.    ,
        0.    ,
        0.    ,
        0.
    ]
)

soc_base_simple = np.array(
    [
        0.5       ,
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
        0.            ,
        20047.11229812,
        20047.95046608,
        20048.77886147,
        20049.59760268,
        20050.40680666,
        20051.20658894,
        15990.37116823,
        -4983.52093018,
        -323.83088639 ,
        -459.97259284 ,
    ]
)

reject_base_lib = np.array(
    [
        0.00000000e+00,
        2.99528877e+04,
        7.99520495e+04,
        7.99512211e+04,
        5.89504024e+04,
        3.79495932e+04,
        1.69487934e+04,
        9.62883177e+00,
        -1.64790698e+01,
        2.36120986e-01,
        -1.16863220e-02,
    ]
)

soc_base_lib = np.array(
    [
        0.5       ,
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
    "SB.cycle_usage_perc":  0.43865238718777017,
    "SB.total_time_usage":  20.0,
    "SB.time_usage_perc":  63.41958396752917,
    "SB.SOC (1)":  0.18644728149025358,
    "SB.SOC (2)":  0.15097155977675195,
}

def test_SimpleBattery_regression_():

    dt = 0.5

    battery = SimpleBattery(test_input_dict, dt)

    times_test = np.arange(0, 5.5, dt)
    powers_test = np.zeros_like(times_test)
    reject_test = np.zeros_like(times_test)
    soc_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = battery.step({
            "time": t,
            "py_sims": {
                "inputs": {
                    "battery_signal": powers_requested[i],
                    "locally_generated_power": powers_requested[i]
                }
            }
        })
        powers_test[i] = out["power"]
        reject_test[i] = out["reject"]
        soc_test[i] = out["soc"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("Rejected: ", reject_test)
        print("SOC: ", soc_test)

    assert np.allclose(powers_base_simple, powers_test)
    assert np.allclose(reject_base_simple, reject_test)
    assert np.allclose(soc_base_simple, soc_test)

def test_LIB_regression_():


    dt = 0.5

    battery = LIB(test_input_dict, dt)

    times_test = np.arange(0, 5.5, dt)
    powers_test = np.zeros_like(times_test)
    reject_test = np.zeros_like(times_test)
    soc_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = battery.step({
            "time": t,
            "py_sims": {
                "inputs": {
                    "battery_signal": powers_requested[i],
                    "locally_generated_power": powers_requested[i]
                }
            }
        })
        powers_test[i] = out["power"]
        reject_test[i] = out["reject"]
        soc_test[i] = out["soc"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("Rejected: ", reject_test)
        print("SOC: ", soc_test)

    assert np.allclose(powers_base_lib, powers_test)
    assert np.allclose(reject_base_lib, reject_test)
    assert np.allclose(soc_base_lib, soc_test)

def test_SimpleBattery_usage_calc_regression():

    battery_dict = test_input_dict
    dt = 1

    # Modify battery configuration for testing
    battery_dict["size"] = 2
    battery_dict["energy_capacity"] = 8  
    battery_dict["charge_rate"] = 2
    battery_dict["discharge_rate"] = 2
    battery_dict["roundtrip_efficiency"] = 0.9
    battery_dict["self_discharge_time_constant"] = 100
    battery_dict["track_usage"] = True
    battery_dict["usage_calc_interval"] = 10
    battery_dict["usage_lifetime"] = 0.000001
    battery_dict["usage_cycles"] = 5
    battery_dict["initial_conditions"] = {"SOC": 0.23}


    SB = SimpleBattery(battery_dict, dt)

    power_avail = 10e3 * np.ones(21)
    power_signal = [1500, 1500, 1500, -1700, -1700, -1700, 1800, 1800, 1800, 1800, 1800,\
                    -1800, -1800, -1800, -1800, -1800, 1800, 1800, 1800, 1800, 1800]

    for i in range(len(power_avail)):
        step_input_dict = {
            "py_sims": {"inputs": {
                "locally_generated_power": power_avail[i],
                "battery_signal": power_signal[i]
                }
            },
        }
        out = SB.step(step_input_dict)
        # assert out["power"] == power_signal[i]
    
    assert SB.step_counter == 1
    assert out["power"] == usage_calc_base_dict["out_power"]

    assert SB.total_cycle_usage == usage_calc_base_dict["SB.total_cycle_usage"]
    assert SB.cycle_usage_perc == usage_calc_base_dict["SB.cycle_usage_perc"]
    assert SB.total_time_usage == usage_calc_base_dict["SB.total_time_usage"]
    assert SB.time_usage_perc == usage_calc_base_dict["SB.time_usage_perc"]

    assert SB.SOC == usage_calc_base_dict["SB.SOC (1)"]

    if PRINT_VALUES:
        print("out_power: ", out["power"])
        print("SB.total_cycle_usage: ", SB.total_cycle_usage)
        print("SB.cycle_usage_perc: ", SB.cycle_usage_perc)
        print("SB.total_time_usage: ", SB.total_time_usage)
        print("SB.time_usage_perc: ", SB.time_usage_perc)
        print("SB.SOC (1): ", SB.SOC)
    
    for i in range(len(power_avail)):
        step_input_dict = {
            "py_sims": {"inputs": {
                "locally_generated_power": power_avail[i],
                "battery_signal": 0
                }
            },
        }
        out = SB.step(step_input_dict)
    assert SB.SOC == usage_calc_base_dict["SB.SOC (2)"]

    if PRINT_VALUES:
        print("SB.SOC (2): ", SB.SOC)
