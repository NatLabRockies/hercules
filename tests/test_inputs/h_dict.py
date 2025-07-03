# Define a test h_dict

plant = {
    'interconnect_limit' : 30000.0
}

wind_farm = {
    'py_sim_type': 'WindSimLongTerm',
    'num_turbines': 3,
    'floris_input_file': 'test_inputs/floris_input.yaml',
    'wind_input_file': 'test_inputs/wind_input.p',
    'turbine_file_name': 'test_inputs/turbine_filter_model.yaml',
    'log_file_name' : 'outputs/wind_farm.log'
}


h_dict = {
    'dt': 1.0,
    'starttime': 0.0,
    'endtime': 10.0,
    'verbose': False,
    'step': 2,
    'time': 2.0,
    'plant': plant,
    
}