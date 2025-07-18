# Define a test h_dict

plant = {"interconnect_limit": 30000.0}

wind_farm = {
    "py_sim_type": "WindSimLongTerm",
    "floris_input_file": "tests/test_inputs/floris_input.yaml",
    "wind_input_filename": "tests/test_inputs/wind_input.csv",
    "turbine_file_name": "tests/test_inputs/turbine_filter_model.yaml",
    "log_file_name": "outputs/wind_farm.log",
}



solar_farm_pysam = {
    "py_sim_type": "SolarPySAM",
    "pysam_model": "pvwatts",
    "solar_input_filename": "tests/test_inputs/solar_pysam_data.csv",
    "target_system_capacity": 100.0,
    "target_dc_ac_ratio": 1.2,
    "lat": 39.742,
    "lon": -105.179,
    "elev": 1828.8,
    "initial_conditions": {"power": 0.0, "dni": 0.0, "poa": 0.0},
}

solar_farm_pvsam = {
    "py_sim_type": "SolarPySAM",
    "pysam_model": "pvsam",
    "solar_input_filename": None,
    "weather_data_input": {
        "time": [0],
        "time_utc": ["2018-05-10 12:31:00+00:00"],
        "SRRL BMS Direct Normal Irradiance (W/m²_irr)": [330.8601989746094],
        "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": [32.576671600341804],
        "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": [68.23037719726561],
        "SRRL BMS Wind Speed at 19' (m/s)": [0.4400002620664621],
        "SRRL BMS Dry Bulb Temperature (°C)": [11.990000406901045],
    },
    "system_info_file_name": "tests/test_inputs/100MW_1axis_pvsamv1.json",
    "lat": 39.7442,
    "lon": -105.1778,
    "elev": 1829,
    "target_system_capacity": 100002.58266599999,
    "target_dc_ac_ratio": 1.33,
    "initial_conditions": {"power": 25, "dni": 1000, "poa": 1000},
}

solar_farm_pvwatts = {
    "py_sim_type": "SolarPySAM",
    "pysam_model": "pvwatts",
    "solar_input_filename": None,
    "weather_data_input": {
        "time": [0],
        "time_utc": ["2018-05-10 12:31:00+00:00"],
        "SRRL BMS Direct Normal Irradiance (W/m²_irr)": [330.8601989746094],
        "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": [32.576671600341804],
        "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": [68.23037719726561],
        "SRRL BMS Wind Speed at 19' (m/s)": [0.4400002620664621],
        "SRRL BMS Dry Bulb Temperature (°C)": [11.990000406901045],
    },
    "lat": 39.7442,
    "lon": -105.1778,
    "elev": 1829,
    "target_system_capacity": 100002.58266599999,
    "target_dc_ac_ratio": 1.33,
    "initial_conditions": {"power": 25, "dni": 1000, "poa": 1000},
}

battery = {
    "py_sim_type": "SimpleBattery",
    "energy_capacity": 100.0,
    "charge_rate": 50.0,
    "discharge_rate": 50.0,
    "max_SOC": 0.9,
    "min_SOC": 0.1,
    "initial_conditions": {"SOC": 0.5},
}

simple_battery = {
    "py_sim_type": "SimpleBattery",
    "size": 20,  # MW size of the battery
    "energy_capacity": 80,  # total capacity of the battery in MWh
    "charge_rate": 2,  # charge rate in MW
    "discharge_rate": 2,  # discharge rate in MW
    "max_SOC": 0.9,  # upper boundary on battery SOC
    "min_SOC": 0.1,  # lower boundary on battery SOC
    "initial_conditions": {"SOC": 0.102},
}

lib_battery = {
    "py_sim_type": "LIB",
    "size": 20,  # MW size of the battery
    "energy_capacity": 80,  # total capacity of the battery in MWh
    "charge_rate": 2,  # charge rate in MW
    "discharge_rate": 2,  # discharge rate in MW
    "max_SOC": 0.9,  # upper boundary on battery SOC
    "min_SOC": 0.1,  # lower boundary on battery SOC
    "initial_conditions": {"SOC": 0.102},
}

electrolyzer = {
    # 'py_sim_type': 'ElectrolyzerPlant',  # Removed for Supervisor compatibility
    "initialize": True,
    "initial_power_kW": 3000,
    "supervisor": {
        "n_stacks": 10,
    },
    "stack": {
        "cell_type": "PEM",
        "cell_area": 1000.0,
        "max_current": 2000,
        "temperature": 60,
        "n_cells": 100,
        "min_power": 50,
        "stack_rating_kW": 500,
        "include_degradation_penalty": True,
    },
    "controller": {
        "n_stacks": 10,
        "control_type": "DecisionControl",
        "policy": {
            "eager_on": False,
            "eager_off": False,
            "sequential": False,
            "even_dist": False,
            "baseline": True,
        },
    },
    "costs": None,
    "cell_params": {
        "cell_type": "PEM",
        "PEM_params": {
            "cell_area": 1000,
            "turndown_ratio": 0.1,
            "max_current_density": 2,
        },
    },
    "degradation": {
        "PEM_params": {
            "rate_steady": 1.41737929e-10,
            "rate_fatigue": 3.33330244e-07,
            "rate_onoff": 1.47821515e-04,
        },
    },
}

# Base h_dict with no py_sims
h_dict = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
}

# h_dict with wind_farm only
h_dict_wind = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "wind_farm": wind_farm,
}

# h_dict with solar_farm only
h_dict_solar = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 6.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "solar_farm": solar_farm_pysam,
}

# h_dict with solar_farm_pysam only
h_dict_solar_pysam = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 6.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "solar_farm": solar_farm_pysam,
}

# h_dict with solar_farm_pvsam only (for original test compatibility)
h_dict_solar_pvsam = {
    "dt": 0.5,
    "starttime": 0.0,
    "endtime": 0.5,
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "solar_farm": solar_farm_pvsam,
}

# h_dict with solar_farm_pvwatts only
h_dict_solar_pvwatts = {
    "dt": 0.5,
    "starttime": 0.0,
    "endtime": 0.5,
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "solar_farm": solar_farm_pvwatts,
}

# h_dict with battery only
h_dict_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "battery": battery,
}

# h_dict with all three py_sims
h_dict_wind_solar_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 6.0,
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "wind_farm": wind_farm,
    "solar_farm": solar_farm_pysam,
    "battery": battery,
}

h_dict_simple_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "battery": simple_battery,
}

h_dict_lib_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "battery": lib_battery,
}

h_dict_electrolyzer = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "electrolyzer": electrolyzer,
}
