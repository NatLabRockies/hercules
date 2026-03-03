# Define test h_dict fixtures for unit tests
#
# IMPORTANT: These are POST-LOADING test fixtures that mimic the h_dict structure
# AFTER it has been processed by load_hercules_input().
#
# They contain BOTH:
#   - starttime_utc/endtime_utc: pd.Timestamp objects (as created by load_hercules_input)
#   - starttime/endtime: Computed values (numeric, in seconds from t=0)
#
# Real YAML input files should ONLY contain starttime_utc and endtime_utc as strings.
# The load_hercules_input() function converts them to pd.Timestamp objects and
# computes starttime (always 0.0) and endtime (duration in seconds) automatically.
#
# These test fixtures bypass load_hercules_input() for efficiency, so they
# need to have both sets of values pre-populated.

import pandas as pd

plant = {"interconnect_limit": 30000.0}

wind_farm = {
    "component_type": "WindFarm",
    "floris_input_file": "tests/test_inputs/floris_input.yaml",
    "wind_input_filename": "tests/test_inputs/wind_input.csv",
    "turbine_file_name": "tests/test_inputs/turbine_filter_model.yaml",
    "log_file_name": "outputs/wind_farm.log",
    "log_channels": [
        "power",
        "wind_speed_mean_background",
        "wind_speed_mean_withwakes",
        "wind_direction_mean",
        "turbine_powers",
    ],
    "floris_update_time_s": 30.0,  # Required parameter for FLORIS updates
}


solar_farm_pysam = {
    "component_type": "SolarPySAMPVWatts",
    "solar_input_filename": "tests/test_inputs/solar_pysam_data.csv",
    "system_capacity": 100.0,  # kW
    "tilt": 0,  # degrees
    "lat": 39.742,
    "lon": -105.179,
    "elev": 1828.8,
    "losses": 0,
    "log_channels": ["power", "dni", "poa", "aoi"],
    "initial_conditions": {"power": 0.0, "dni": 0.0, "poa": 0.0},
}

solar_farm_pvwatts = {
    "component_type": "SolarPySAMPVWatts",
    "solar_input_filename": "tests/test_inputs/solar_pysam_data.csv",
    "lat": 39.7442,
    "lon": -105.1778,
    "elev": 1829,
    "system_capacity": 100000.0,  # kW (100 MW)
    "tilt": 0,  # degrees
    "losses": 0,
    "log_channels": ["power", "dni", "poa", "aoi"],
    "initial_conditions": {"power": 25, "dni": 1000, "poa": 1000},
}

battery = {
    "component_type": "BatterySimple",
    "energy_capacity": 100.0,
    "charge_rate": 50.0,
    "discharge_rate": 50.0,
    "max_SOC": 0.9,
    "min_SOC": 0.1,
    "log_channels": ["power", "soc", "power_setpoint"],
    "initial_conditions": {"SOC": 0.5},
}

simple_battery = {
    "component_type": "BatterySimple",
    "size": 20000,  # kW size of the battery (20 MW)
    "energy_capacity": 80000,  # total capacity of the battery in kWh (80 MWh)
    "charge_rate": 2000,  # charge rate in kW (2 MW)
    "discharge_rate": 2000,  # discharge rate in kW (2 MW)
    "max_SOC": 0.9,  # upper boundary on battery SOC
    "min_SOC": 0.1,  # lower boundary on battery SOC
    "log_channels": ["power", "soc", "power_setpoint"],
    "initial_conditions": {"SOC": 0.102},
}

lib_battery = {
    "component_type": "BatteryLithiumIon",
    "size": 20000,  # kW size of the battery (20 MW)
    "energy_capacity": 80000,  # total capacity of the battery in kWh (80 MWh)
    "charge_rate": 2000,  # charge rate in kW (2 MW)
    "discharge_rate": 2000,  # discharge rate in kW (2 MW)
    "max_SOC": 0.9,  # upper boundary on battery SOC
    "min_SOC": 0.1,  # lower boundary on battery SOC
    "log_channels": ["power", "soc", "power_setpoint"],
    "initial_conditions": {"SOC": 0.102},
}


thermal_component = {
    "component_type": "ThermalComponentBase",
    "rated_capacity": 1000,  # kW (1 MW)
    "min_stable_load_fraction": 0.20,  # 20% minimum operating point
    "ramp_rate_fraction": 0.50,  # 50% of rated capacity per minute
    "run_up_rate_fraction": 0.20,  # 20% of rated capacity per minute
    "hot_startup_time": 120.0,  # s (must be >= run_up_rate_fraction of 60s)
    "warm_startup_time": 120.0,  # s (must be >= ramp_time of 60s)
    "cold_startup_time": 120.0,  # s (must be >= ramp_time of 60s)
    "min_up_time": 10.0,  # s
    "min_down_time": 10.0,  # s
    "log_channels": [
        "power",
        "state",
        "efficiency",
        "fuel_volume_rate",
        "fuel_mass_rate",
    ],
    "initial_conditions": {"power": 1000},  # power > 0 implies ON state
    "hhv": 40000000,  # J/m³ (made up round number for testing, NOT realistic)
    "fuel_density": 1.0,  # kg/m³ (made up round number for testing, NOT realistic)
    # HHV net efficiency values (made up round numbers for testing, NOT realistic)
    "efficiency_table": {
        "power_fraction": [1.0, 0.75, 0.50, 0.25],
        "efficiency": [0.40, 0.38, 0.35, 0.30],
    },
}


open_cycle_gas_turbine = {
    "component_type": "OpenCycleGasTurbine",
    "rated_capacity": 1000,  # kW (1 MW)
    "min_stable_load_fraction": 0.20,  # 20% minimum operating point
    "ramp_rate_fraction": 0.50,  # 50% of rated capacity per minute
    "run_up_rate_fraction": 0.20,  # 20% of rated capacity per minute
    "hot_startup_time": 120.0,  # s (must be >= run_up_rate_fraction of 60s)
    "warm_startup_time": 120.0,  # s (must be >= ramp_time of 60s)
    "cold_startup_time": 120.0,  # s (must be >= ramp_time of 60s)
    "min_up_time": 10.0,  # s
    "min_down_time": 10.0,  # s
    "log_channels": [
        "power",
        "state",
        "efficiency",
        "fuel_volume_rate",
        "fuel_mass_rate",
    ],
    "initial_conditions": {"power": 1000},  # power > 0 implies ON state
    "hhv": 39050000,  # J/m³ (natural gas HHV from [6])
    # HHV net plant efficiency from SC1A curve in Exhibit ES-4 of [5]
    "efficiency_table": {
        "power_fraction": [1.0, 0.75, 0.50, 0.25],
        "efficiency": [0.39, 0.37, 0.325, 0.245],
    },
}


combined_cycle_gas_turbine = {
    "component_type": "CombinedCycleGasTurbine",
    "rated_capacity": 1000,  # kW (1 MW)
    "min_stable_load_fraction": 0.40,  # 40% minimum operating point
    "ramp_rate_fraction": 0.10,  # 10% of rated capacity per minute
    "run_up_rate_fraction": 0.05,  # 5% of rated capacity per minute
    "hot_startup_time": 1200.0,  # s (must be >= run_up_rate_fraction of 60s)
    "warm_startup_time": 1200.0,  # s (must be >= ramp_time of 60s)
    "cold_startup_time": 1200.0,  # s (must be >= ramp_time of 60s)
    "min_up_time": 10.0,  # s
    "min_down_time": 10.0,  # s
    "log_channels": [
        "power",
        "state",
        "efficiency",
        "fuel_volume_rate",
        "fuel_mass_rate",
    ],
    "initial_conditions": {"power": 1000},  # power > 0 implies ON state
    "hhv": 39050000,  # J/m³ (natural gas HHV from [6])
    # HHV net plant efficiency from SC1A curve in Exhibit ES-4 of [5]
    "efficiency_table": {
        "power_fraction": [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.7, 0.65, 0.6, 0.55, 0.50, 0.4],
        "efficiency": [0.53, 0.515, 0.52, 0.52, 0.52, 0.52, 0.52, 0.515, 0.505, 0.5, 0.49, 0.47],
    },
}


electrolyzer = {
    "component_type": "ElectrolyzerPlant",
    "initial_conditions": {
        "power_available_kW": 3000,
    },
    "log_channels": ["power"],
    "electrolyzer": {
        "initialize": True,
        "initial_power_kW": 3000,
        "supervisor": {
            "n_stacks": 10,
            "system_rating_MW": 5.0,
        },
        "stack": {
            "cell_type": "PEM",
            "max_current": 2000,
            "temperature": 60,
            "n_cells": 100,
            "stack_rating_kW": 500,
            "include_degradation_penalty": True,
        },
        "controller": {
            "control_type": "DecisionControl",
            "policy": {
                "eager_on": False,
                "eager_off": False,
                "sequential": False,
                "even_dist": False,
                "baseline": True,
            },
        },
        "cell_params": {
            "cell_type": "PEM",
            "max_current_density": 2.0,
            "PEM_params": {
                "cell_area": 1000,
                "turndown_ratio": 0.1,
                "max_current_density": 2,
                "p_anode": 1.01325,
                "p_cathode": 30,
                "alpha_a": 2,
                "alpha_c": 0.5,
                "i_0_a": 2.0e-7,
                "i_0_c": 2.0e-3,
                "e_m": 0.02,
                "R_ohmic_elec": 50.0e-3,
                "f_1": 250,
                "f_2": 0.996,
            },
        },
        "degradation": {
            "eol_eff_percent_loss": 10,
            "PEM_params": {
                "rate_steady": 1.41737929e-10,
                "rate_fatigue": 3.33330244e-07,
                "rate_onoff": 1.47821515e-04,
            },
        },
    },
}

# Base h_dict with no components
h_dict = {
    "dt": 1.0,
    # "starttime": 0.0,
    # "endtime": 30.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:30", utc=True),
    "plant": plant,
    "verbose": False,
}

# h_dict with wind_farm only
# Time range: 0-10 seconds, starting at 2018-05-10 12:31:00
h_dict_wind = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "wind_farm": wind_farm,
}

# h_dict with solar_farm only
# Time range: 0-6 seconds, starting at 2018-05-10 12:31:00
h_dict_solar = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 6.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:06", utc=True),
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
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:06", utc=True),
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "solar_farm": solar_farm_pysam,
}

# h_dict with solar_farm_pvwatts only
h_dict_solar_pvwatts = {
    "dt": 0.5,
    "starttime": 0.0,
    "endtime": 0.5,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:00.500000", utc=True),
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "solar_farm": solar_farm_pvwatts,
}

# Note: h_dict_solar_pvwatts_max was removed - tests should create their own precise conditions

# h_dict with battery only
h_dict_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 2,
    "time": 2.0,
    "plant": plant,
    "battery": battery,
}

# h_dict with all three components
h_dict_wind_solar_battery = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 6.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:06", utc=True),
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
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
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
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
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
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "electrolyzer": electrolyzer,
}


h_dict_thermal_component = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "thermal_component": thermal_component,
}

h_dict_open_cycle_gas_turbine = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "open_cycle_gas_turbine": open_cycle_gas_turbine,
}

h_dict_combined_cycle_gas_turbine = {
    "dt": 1.0,
    "starttime": 0.0,
    "endtime": 10.0,
    "starttime_utc": pd.to_datetime("2018-05-10 12:31:00", utc=True),
    "endtime_utc": pd.to_datetime("2018-05-10 12:31:10", utc=True),
    "verbose": False,
    "step": 0,
    "time": 0.0,
    "plant": plant,
    "combined_cycle_gas_turbine": combined_cycle_gas_turbine,
}
