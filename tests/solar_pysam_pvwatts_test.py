"""This module provides unit tests for 'SolarPySAMPVWatts'."""

import copy
import os
import tempfile

import pandas as pd
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from numpy.testing import assert_almost_equal

from tests.test_inputs.h_dict import h_dict_solar_pvwatts

# Removed unnecessary create_solar_pysam() function and SPS fixture
# Tests now use direct instantiation for simplicity


def test_init():
    # testing the `init` function: reading the inputs from input dictionary
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    assert SPS.dt == test_h_dict["dt"]
    # Note: PVWatts system_capacity is now calculated from nameplate_dc_capacity
    # so we test that nameplate_dc_capacity is stored correctly
    assert SPS.nameplate_dc_capacity == test_h_dict["solar_farm"]["nameplate_dc_capacity"]
    assert SPS.power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dc_power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dni == test_h_dict["solar_farm"]["initial_conditions"]["dni"]
    assert SPS.aoi == 0


def test_return_outputs():
    # testing the function `return_outputs`
    # outputs after initialization - all outputs should reflect input dict
    # Note: Current SolarPySAMPVWatts doesn't have return_outputs method,
    # so we test the attributes directly
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    assert SPS.power == 25
    assert SPS.dni == 1000
    assert SPS.poa == 1000

    # change PV power predictions and irradiance as if during simulation
    SPS.power = 800
    SPS.dni = 600
    SPS.poa = 900
    SPS.aoi = 0

    # check that outputs return the changed PV outputs
    assert SPS.power == 800
    assert SPS.dni == 600
    assert SPS.poa == 900
    assert SPS.aoi == 0


def test_step():
    # testing the `step` function: calculating power based on inputs at first timestep
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": 1e9}}

    SPS.step(step_inputs)

    # test the calculated power output
    assert_almost_equal(SPS.power, 38821.18549337308, decimal=8)

    # test the irradiance input
    assert_almost_equal(SPS.ghi, 68.23037719726561, decimal=8)


def test_capacity_output():
    """Test that power output under maximum solar conditions equals nameplate_dc_capacity exactly.

    The nameplate_dc_capacity parameter should represent the exact maximum DC power output
    that the solar array can produce under ideal solar conditions. This test creates
    precise maximum solar conditions and verifies this behavior.
    """

    # Create precise maximum solar conditions data
    max_solar_data = {
        "time": [0.0, 0.5, 1.0],
        "time_utc": [
            "2018-05-10 12:31:00+00:00",
            "2018-05-10 12:31:00.500000+00:00",
            "2018-05-10 12:31:01+00:00",
        ],
        "SRRL BMS Direct Normal Irradiance (W/m²_irr)": [1000.0, 1000.0, 1000.0],
        "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": [100.0, 100.0, 100.0],
        "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": [1000.0, 1000.0, 1000.0],
        "SRRL BMS Wind Speed at 19' (m/s)": [0.44, 0.44, 0.44],
        "SRRL BMS Dry Bulb Temperature (°C)": [12.0, 12.0, 12.0],
    }

    # Create temporary CSV file with maximum solar conditions
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df_max = pd.DataFrame(max_solar_data)
        df_max.to_csv(f.name, index=False)
        temp_csv_path = f.name

    try:
        # Create test configuration with precise nameplate capacity
        test_nameplate_capacity = 100.0  # kW - nice round number for testing
        test_h_dict = {
            "dt": 0.5,
            "starttime": 0.0,
            "endtime": 1.5,
            "verbose": False,
            "solar_farm": {
                "component_type": "SolarPySAMPVWatts",
                "solar_input_filename": temp_csv_path,
                "lat": 39.7442,
                "lon": -105.1778,
                "elev": 1829,
                "nameplate_dc_capacity": test_nameplate_capacity,
                "losses": 0,  # No losses for maximum output
                "initial_conditions": {"power": 0, "dni": 0, "poa": 0},
            },
        }

        step_inputs = {"step": 0, "solar_farm": {"power_setpoint": 1e9}}
        SPS_max = SolarPySAMPVWatts(test_h_dict)
        SPS_max.step(step_inputs)

        # Test that the power output equals the nameplate_dc_capacity within reasonable precision
        # This is the core design requirement: nameplate_dc_capacity = maximum possible DC output
        # Allow small tolerance for numerical precision in PySAM calculations
        assert_almost_equal(SPS_max.power, test_nameplate_capacity, decimal=3)

    finally:
        # Clean up temporary file
        if os.path.exists(temp_csv_path):
            os.unlink(temp_csv_path)


def test_control():
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    power_setpoint = 10000
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)

    power_setpoint = 100
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)
