"""Regression tests for 'SolarPySAMPVWatts'."""

import os

import numpy as np
import pytest
from hercules.python_simulators.solar_pysam_pvwatts import SolarPySAMPVWatts

PRINT_VALUES = True

powers_base_no_control = np.array(
    [
        13751.39824276,
        13762.28230574,
        13773.16638954,
        13784.0501833,
        13794.93394526,
        13805.81761126,
        13816.70114304,
        13827.58454415,
        13838.4678379,
        13849.35112479,
    ]
)

powers_base_control = np.array(
    [
        13751.39824276,
        13762.28230574,
        13773.16638954,
        13784.0501833,
        13794.93394526,
        13800.0,
        13800.0,
        13800.0,
        13800.0,
        13800.0,
    ]
)

dni_base_no_control = np.array(
    [
        330.86019897,
        331.19604492,
        331.53189087,
        331.86773682,
        332.20358276,
        332.53942871,
        332.87527466,
        333.21112061,
        333.54696655,
        333.8828125,
    ]
)

aoi_base_no_control = np.array(
    [
        67.82689268,
        67.82689265,
        67.8268924,
        67.82689242,
        67.8268923,
        67.82689214,
        67.826892,
        67.82689188,
        67.82689174,
        67.82689143,
    ]
)


def get_solar_params():
    full_path = os.path.realpath(__file__)
    path = os.path.dirname(full_path)

    # explicitly specifying weather inputs from the first timestep of the example file
    solar_dict = {
        "dt": 0.5,
        "starttime": 0.0,
        "endtime": 6.0,
        "verbose": False,
        "solar_farm": {
            "py_sim_type": "SolarPySAMPVWatts",
            "solar_input_filename": path + "/../test_inputs/solar_pysam_data.csv",
            "lat": 39.7442,
            "lon": -105.1778,
            "elev": 1829,
            "target_system_capacity": 100002.58266599999,
            "target_dc_ac_ratio": 1.33,
            "initial_conditions": {"power": 25, "dni": 1000, "poa": 1000},
            "verbose": False,
        },
    }

    return solar_dict


def create_solar_pysam():
    solar_dict = get_solar_params()
    return SolarPySAMPVWatts(solar_dict)


@pytest.fixture
def SPS():
    return create_solar_pysam()


def test_SolarPySAM_regression_no_control(SPS: SolarPySAMPVWatts):
    times_test = np.arange(0, 5, SPS.dt)
    steps_test = list(range(len(times_test)))
    powers_test = np.zeros_like(times_test)
    dni_test = np.zeros_like(times_test)
    aoi_test = np.zeros_like(times_test)

    for step in steps_test:
        out = SPS.step({"step": step, "solar_farm": {}})
        powers_test[step] = out["solar_farm"]["power"]
        dni_test[step] = out["solar_farm"]["dni"]
        aoi_test[step] = out["solar_farm"]["aoi"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("DNI: ", dni_test)
        print("AOI: ", aoi_test)

    assert np.allclose(powers_base_no_control, powers_test)
    assert np.allclose(dni_base_no_control, dni_test)
    assert np.allclose(aoi_base_no_control, aoi_test)


def test_SolarPySAM_regression_control(SPS: SolarPySAMPVWatts):
    power_setpoint = 13800.0  # Slightly below most of the base outputs.

    times_test = np.arange(0, 5, SPS.dt)
    steps_test = list(range(len(times_test)))
    powers_test = np.zeros_like(times_test)
    dni_test = np.zeros_like(times_test)
    aoi_test = np.zeros_like(times_test)

    for step in steps_test:
        out = SPS.step({"step": step, "solar_farm": {"power_setpoint": power_setpoint}})
        powers_test[step] = out["solar_farm"]["power"]
        dni_test[step] = out["solar_farm"]["dni"]
        aoi_test[step] = out["solar_farm"]["aoi"]

    if PRINT_VALUES:
        print("Powers: ", powers_test)
        print("DNI: ", dni_test)
        print("AOI: ", aoi_test)

    assert np.allclose(powers_base_control, powers_test)
    assert np.allclose(dni_base_no_control, dni_test)
    assert np.allclose(aoi_base_no_control, aoi_test)
