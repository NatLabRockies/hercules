from hercules.python_simulators.electrolyzer_plant import ElectrolyzerPlant

test_input_dict = {
    "general": {
        "verbose": False
    },
    "electrolyzer": {
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
    },
}


def test_allow_grid_power_consumption():
    # Test with allow_grid_power_consumption = False
    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    
    step_inputs = {
        "py_sims": {
            "inputs": {
                "locally_generated_power": 3000,
                "electrolyzer_signal": 2000,
            }
        }
    }
    
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_2000 = out["H2_output"]

    # Match locally available power
    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    step_inputs["py_sims"]["inputs"]["electrolyzer_signal"] = 3000
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_3000 = out["H2_output"]

    assert H2_output_3000 > H2_output_2000

    # Ask exceeds locally available power
    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    step_inputs["py_sims"]["inputs"]["electrolyzer_signal"] = 4000
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_4000 = out["H2_output"]
    assert H2_output_4000 == H2_output_3000

    # Now, allow grid charging and repeat tests
    test_input_dict["allow_grid_power_consumption"] = True
    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    
    step_inputs["py_sims"]["inputs"]["electrolyzer_signal"] = 2000
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_2000 = out["H2_output"]
    
    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    step_inputs["py_sims"]["inputs"]["electrolyzer_signal"] = 3000
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_3000 = out["H2_output"]
    assert H2_output_3000 > H2_output_2000

    electrolyzer = ElectrolyzerPlant(test_input_dict, 1)
    step_inputs["py_sims"]["inputs"]["electrolyzer_signal"] = 4000
    for _ in range(100): # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_4000 = out["H2_output"]
    assert H2_output_4000 > H2_output_3000
