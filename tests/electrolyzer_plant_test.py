import copy

from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant

from tests.test_inputs.h_dict import h_dict_electrolyzer


def test_allow_grid_power_consumption():
    # Test with allow_grid_power_consumption = False
    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    electrolyzer = ElectrolyzerPlant(test_h_dict)

    step_inputs = {
        "plant": {
            "locally_generated_power": 3000,
        },
        "electrolyzer": {
            "electrolyzer_signal": 2000,
        },
    }

    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_2000 = out["electrolyzer"]["H2_output"]

    # Match locally available power
    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    electrolyzer = ElectrolyzerPlant(test_h_dict)
    step_inputs["electrolyzer"]["electrolyzer_signal"] = 3000
    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_3000 = out["electrolyzer"]["H2_output"]

    assert H2_output_3000 > H2_output_2000

    # Ask exceeds locally available power
    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    electrolyzer = ElectrolyzerPlant(test_h_dict)
    step_inputs["electrolyzer"]["electrolyzer_signal"] = 4000
    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_4000 = out["electrolyzer"]["H2_output"]
    assert H2_output_4000 == H2_output_3000

    # Now, allow grid charging and repeat tests
    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    test_h_dict["electrolyzer"]["allow_grid_power_consumption"] = True
    electrolyzer = ElectrolyzerPlant(test_h_dict)

    step_inputs["electrolyzer"]["electrolyzer_signal"] = 2000
    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_2000 = out["electrolyzer"]["H2_output"]

    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    test_h_dict["electrolyzer"]["allow_grid_power_consumption"] = True
    electrolyzer = ElectrolyzerPlant(test_h_dict)
    step_inputs["electrolyzer"]["electrolyzer_signal"] = 3000
    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_3000 = out["electrolyzer"]["H2_output"]
    assert H2_output_3000 > H2_output_2000

    test_h_dict = copy.deepcopy(h_dict_electrolyzer)
    test_h_dict["electrolyzer"]["allow_grid_power_consumption"] = True
    electrolyzer = ElectrolyzerPlant(test_h_dict)
    step_inputs["electrolyzer"]["electrolyzer_signal"] = 4000
    for _ in range(100):  # Run 100 steps
        out = electrolyzer.step(step_inputs)
    H2_output_4000 = out["electrolyzer"]["H2_output"]
    assert H2_output_4000 > H2_output_3000
