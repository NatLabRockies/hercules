"""This module provides unit tests for 'SolarPySAM'."""
import os

import pytest
from hercules.python_simulators.solar_pysam import SolarPySAM
from numpy.testing import assert_almost_equal


def get_solar_params():

    full_path = os.path.realpath(__file__)
    path = os.path.dirname(full_path)

    # explicitly specifying weather inputs from the first timestep of the example file
    solar_dict = {
        "py_sim_type": SolarPySAM,
        "pysam_model": "pvsam",
        "solar_input_filename": None,
        "weather_data_input": {
        "time": [0],
        "time_utc": ['2018-05-10 12:31:00+00:00'],
        "SRRL BMS Direct Normal Irradiance (W/m²_irr)": [330.8601989746094],
        "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": [32.576671600341804],
        "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": [68.23037719726561],
        "SRRL BMS Wind Speed at 19' (m/s)": [0.4400002620664621],
        "SRRL BMS Dry Bulb Temperature (°C)": [11.990000406901045],
        },

        "system_info_file_name": path+
            '/../test_inputs/100MW_1axis_pvsamv1.json',
        "lat": 39.7442, 
        "lon": -105.1778, 
        "elev": 1829,
        "target_system_capacity_kW": 100002.58266599999,
        "target_dc_ac_ratio": 1.33,
        "initial_conditions": {
            "power": 25, 
            "dni": 1000,
            "poa": 1000
        },
    }
    
    dt = 0.5 # s - input file has a dt of 1 min

    return solar_dict, dt

def create_solar_pysam():
    solar_dict, dt = get_solar_params()
    return SolarPySAM(solar_dict, dt, starttime=0, endtime=0.5)

@pytest.fixture
def SPS():
    return create_solar_pysam()

def test_init():
    # testing the `init` function: reading the inputs from input dictionary
    solar_dict, dt = get_solar_params()
    SPS = SolarPySAM(solar_dict, dt, starttime=0, endtime=0.5)

    assert SPS.dt == dt

    assert SPS.target_system_capacity == solar_dict["target_system_capacity_kW"]
    assert SPS.power_mw == solar_dict["initial_conditions"]["power"]
    assert SPS.dc_power_mw == solar_dict["initial_conditions"]["power"]
    assert SPS.dni == solar_dict["initial_conditions"]["dni"]
    assert SPS.aoi == 0

def test_return_outputs(SPS: SolarPySAM):
    # testing the function `return_outputs`
    # outputs after initialization - all outputs should reflect input dict
    outputs_init = SPS.return_outputs()

    assert outputs_init["power_mw"] == 25
    assert outputs_init["dni"] == 1000
    assert outputs_init["poa"] == 1000

    # change PV power predictions and irradiance as if during simulation
    SPS.power_mw = 800
    SPS.dni = 600
    SPS.poa = 900
    SPS.aoi = 0

    # check that outputs return the changed PV outputs
    outputs_sim = SPS.return_outputs()

    assert outputs_sim["power_mw"] == 800
    assert outputs_sim["dni"] == 600
    assert outputs_sim["poa"] == 900
    assert outputs_sim["aoi"] == 0

def test_step(SPS: SolarPySAM):
    # testing the `step` function: calculating power based on inputs at first timestep
    step_inputs = {"step": 0}

    SPS.step(step_inputs)

    # test that system capacity of model matches the input target_system_capacity
    assert_almost_equal(SPS.system_model.SystemDesign.system_capacity, SPS.target_system_capacity)

    # test the calculated power output
    assert_almost_equal(SPS.power_mw, 14.523542232511712, decimal=8)

    # test the irradiance input
    assert_almost_equal(SPS.ghi, 68.23037719726561, decimal=8)

def test_control(SPS: SolarPySAM):
    power_setpoint_mw = 12
    step_inputs = {"step": 0, "py_sims": {"inputs": {"solar_setpoint_mw": power_setpoint_mw}}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power_mw, power_setpoint_mw, decimal=8)
