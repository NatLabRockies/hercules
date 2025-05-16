from hercules.controller_standin import ControllerStandin
from hercules.emulator import Emulator
from hercules.py_sims import PySims

# Copy data from hercules_input.yaml into input_dict
test_input_dict = {
    "name": "test_input_dict",
    "description": "Test input dictionary for Hercules",
    "dt": 1,
    "starttime": 0.0,
    "endtime": 10.0,
    "hercules_comms": {
        "amr_wind": {
            "test_farm": {
                "type": "amr_wind",
                # requires running pytest from the top level directory
                "amr_wind_input_file": "tests/test_inputs/amr_input_florisstandin.inp",
            }
        },
        "helics": {
            "config": {
                "name": "hercules",
                "use_dash_frontend": False,
                "KAFKA": False,
                "KAFKA_topics": "EMUV1py",
                "helics": { 
                    # deltat: 1 # This will be assigned in software
                    "subscription_topics": ["status"],
                    "publication_topics": ["control"],
                    "endpoints": [],
                    "helicsport" : 32000,
                },
                "publication_interval": 1,
                "endpoint_interval": 1,
                "starttime": 0,
                "stoptime": 100,
                "Agent": "ControlCenter",
            },
        },
    },
    "py_sims": {
        "test_solar": {
            "py_sim_type": "SimpleSolar",
            "capacity": 50,
            "efficiency": 0.5,
            "initial_conditions": {
                "power": 10.0,
                "irradiance": 1000,
            },
        }
    },
    "controller": {
        "num_turbines": 2,
        "initial_conditions": {
            "yaw": [270.0, 270.0],
        },
    },
}

def test_Emulator_instantiation():
    
    
    controller = ControllerStandin(test_input_dict)
    py_sims = PySims(test_input_dict)
    
    emulator = Emulator(controller, py_sims, test_input_dict)

    # Check default settings
    assert emulator.output_file == "outputs/hercules_output.csv"
    assert emulator.external_data_all == {}

    test_input_dict_2 = test_input_dict.copy()
    test_input_dict_2["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_input_dict_2["output_file"] = "test_output.csv"
    test_input_dict_2["dt"] = 0.5
    test_input_dict_2["starttime"] = 0.0
    test_input_dict_2["endtime"] = 10.0

    emulator = Emulator(controller, py_sims, test_input_dict_2)

    assert emulator.external_data_all["power_reference"][0] == 1000
    assert emulator.external_data_all["power_reference"][1] == 1500
    assert emulator.external_data_all["power_reference"][2] == 2000
    assert emulator.external_data_all["power_reference"][-1] == 3000

    assert emulator.output_file == "test_output.csv"
