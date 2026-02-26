"""Regression tests for 'SolarPySAMPVWatts'."""

import os

import numpy as np
import pandas as pd
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts

PRINT_VALUES = True

powers_base_no_control = np.array(
    [
        16528.82749492729,
        16541.958599140045,
        16555.08955834377,
        16568.220372741496,
        16581.35104253094,
        16594.481567904546,
        16607.61194537151,
        16620.74217922295,
        16633.872269119838,
        16647.002215233784,
    ]
)

powers_base_control = np.array(
    [
        13800.0,
        13800.0,
        13800.0,
        13800.0,
        13800.0,
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
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
        67.82689268,
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
            "component_type": "SolarPySAMPVWatts",
            "solar_input_filename": path + "/../test_inputs/solar_pysam_data.csv",
            "lat": 39.7442,
            "lon": -105.1778,
            "elev": 1829,
            "system_capacity": 100000.0,  # kW (100 MW)
            "tilt": 0,  # degrees
            "losses": 0,
            "initial_conditions": {"power": 25, "dni": 1000, "poa": 1000},
            "verbose": False,
        },
    }

    # Derive starttime_utc and endtime_utc from the input file to satisfy model requirements
    df = pd.read_csv(solar_dict["solar_farm"]["solar_input_filename"])
    if "time_utc" not in df.columns:
        raise ValueError("Test input solar_pysam_data.csv must include a 'time_utc' column")
    if not pd.api.types.is_datetime64_any_dtype(df["time_utc"]):
        df["time_utc"] = pd.to_datetime(df["time_utc"], format="ISO8601", utc=True)
    start_ts = df["time_utc"].min()
    solar_dict["starttime_utc"] = start_ts.isoformat()
    end_ts = start_ts + pd.to_timedelta(solar_dict["endtime"], unit="s")
    solar_dict["endtime_utc"] = end_ts.isoformat()

    return solar_dict


def test_SolarPySAM_regression_control():
    solar_dict = get_solar_params()
    SPS = SolarPySAMPVWatts(solar_dict, "solar_farm")

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
