# Define a test h_dict

plant = {
    'interconnect_limit' : 30000.0
}

wind_farm = {
    'py_sim_type': 'WindSimLongTerm',
    'num_turbines': 3,
    'floris_input_file': 'tests/test_inputs/floris_input.yaml',
    'wind_input_filename': 'tests/test_inputs/wind_input.csv',
    'turbine_file_name': 'tests/test_inputs/turbine_filter_model.yaml',
    'log_file_name' : 'outputs/wind_farm.log'
}

solar_farm = {
    'py_sim_type': 'SimpleSolar',
    'capacity': 50.0,
    'efficiency': 0.15,
    'area': 1000.0
}

battery = {
    'py_sim_type': 'SimpleBattery',
    'capacity': 100.0,
    'max_power': 50.0,
    'initial_soc': 0.5,
    'min_soc': 0.1,
    'max_soc': 0.9
}

# Base h_dict with no py_sims
h_dict = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant
}

# h_dict with wind_farm only
h_dict_wind = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant,
    'wind_farm': wind_farm
}

# h_dict with solar_farm only
h_dict_solar = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant,
    'solar_farm': solar_farm
}

# h_dict with battery only
h_dict_battery = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant,
    'battery': battery
}

# h_dict with all three py_sims
h_dict_wind_solar_battery = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant,
    'wind_farm': wind_farm,
    'solar_farm': solar_farm,
    'battery': battery
}