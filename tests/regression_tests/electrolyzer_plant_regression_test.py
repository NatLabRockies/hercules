"""Regression tests for 'SolarPySAM'."""

import numpy as np
from hercules.python_simulators.electrolyzer_plant import ElectrolyzerPlant

PRINT_VALUES = True

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

np.random.seed(0)
locally_generated_power_test = np.concatenate(
    (
        np.linspace(500, 1000, 3), # Ramp up
        np.linspace(1000, 200, 3), # Ramp down
        np.ones(3) * 200, # Constant
        np.random.normal(500, 100, 3) # Random fluctuations
    )
)

H2_output_base = np.array(
    [
        0.00071706,
        0.00073655,
        0.00079499,
        0.00088781,
        0.0009718 ,
        0.00098348,
        0.00092732,
        0.00087651,
        0.00083054,
        0.00078894,
        0.00083047,
        0.00084576,
    ]
)

stacks_on_base = np.array([7., 7., 7., 7., 7., 7., 7., 7., 7., 7., 7., 7.])

def test_ElectrolyzerPlant_regression_():

    dt = 0.5

    electrolyzer = ElectrolyzerPlant(test_input_dict, dt)

    times_test = np.arange(0, 6.0, dt)
    H2_output_test = np.zeros_like(times_test)
    stacks_on_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = electrolyzer.step({
            "time": t,
            "py_sims": {
                "inputs": {
                    "locally_generated_power": locally_generated_power_test[i],
                    "electrolyzer_signal": np.inf # Use all locally generated power
                }
            }
        })
        H2_output_test[i] = out["H2_output"]
        stacks_on_test[i] = out["stacks_on"]

        #print(out["H2_output"])

    if PRINT_VALUES:
        print("H2 output: ", H2_output_test)
        print("Stacks on: ", stacks_on_test)

    assert np.allclose(H2_output_base, H2_output_test)
    assert np.allclose(stacks_on_base, stacks_on_test)
