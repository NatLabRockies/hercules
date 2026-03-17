"""Regression tests for 'SolarPySAM'."""

import numpy as np
from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant

PRINT_VALUES = True

test_h_dict = {
    "dt": 0.5,
    "starttime": 0.0,
    "endtime": 10.0,
    "verbose": False,
    "general": {"verbose": False},
    "electrolyzer": {
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
    },
}

np.random.seed(0)
locally_generated_power_test = np.concatenate(
    (
        np.linspace(1000, 3500, 6),  # Ramp up
        np.linspace(3500, 600, 6),  # Ramp down
        np.ones(6) * 600,  # Constant
        np.random.normal(2000, 100, 6),  # Random fluctuations
    )
)

H2_output_base = np.array(
    [
        0.00223303,
        0.00220072,
        0.00225428,
        0.00238206,
        0.00257352,
        0.00281915,
        0.00311032,
        0.00337378,
        0.0035319,
        0.00359005,
        0.00355308,
        0.00342535,
        0.00321079,
        0.00301664,
        0.00284096,
        0.00268201,
        0.00253818,
        0.00240803,
        0.00229027,
        0.00244178,
        0.00255792,
        0.00267192,
        0.00279438,
        0.00289949,
    ]
)

stacks_on_base = np.array(
    [
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
        7.0,
    ]
)

H2_mfr_base = np.array(
    [
        0.00446606,
        0.00440144,
        0.00450856,
        0.00476412,
        0.00514704,
        0.0056383,
        0.00622064,
        0.00674756,
        0.0070638,
        0.0071801,
        0.00710616,
        0.0068507,
        0.00642158,
        0.00603328,
        0.00568192,
        0.00536402,
        0.00507636,
        0.00481606,
        0.00458054,
        0.00488356,
        0.00511584,
        0.00534384,
        0.00558876,
        0.00579898,
    ]
)


def test_ElectrolyzerPlant_regression_():
    electrolyzer = ElectrolyzerPlant(test_h_dict, "electrolyzer")

    times_test = np.arange(0, 12.0, test_h_dict["dt"])
    H2_output_test = np.zeros_like(times_test)
    H2_mfr_test = np.zeros_like(times_test)
    stacks_on_test = np.zeros_like(times_test)

    for i, t in enumerate(times_test):
        out = electrolyzer.step(
            {
                "time": t,
                "plant": {
                    "locally_generated_power": locally_generated_power_test[i],
                },
                "electrolyzer": {
                    "electrolyzer_signal": np.inf  # Use all locally generated power
                },
            }
        )
        H2_output_test[i] = out["electrolyzer"]["H2_output"]
        H2_mfr_test[i] = out["electrolyzer"]["H2_mfr"]
        stacks_on_test[i] = out["electrolyzer"]["stacks_on"]

        # print(out["H2_output"])

    if PRINT_VALUES:
        print("H2 output: ", H2_output_test)
        print("Stacks on: ", stacks_on_test)
        print("H2 mfr: ", H2_mfr_test)

    assert np.allclose(H2_output_base, H2_output_test)
    assert np.allclose(stacks_on_base, stacks_on_test)
