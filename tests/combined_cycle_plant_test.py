import copy

import pytest
from hercules.plant_components.combined_cycle_plant import CombinedCyclePlant

from .test_inputs.h_dict import (
    h_dict_combined_cycle_plant,
    simple_battery,
)


def test_init_from_dict():
    # Set up a system with one OCGT and one steam turbine.
    h_dict = copy.deepcopy(h_dict_combined_cycle_plant)
    CombinedCyclePlant(h_dict, "combined_cycle_plant")


def test_invalid_unit_type():
    h_dict = copy.deepcopy(h_dict_combined_cycle_plant)

    # Wrong types of units to make up the combined cycle plant
    h_dict["combined_cycle_plant"]["units"] = ["open_cycle_gas_turbine", "open_cycle_gas_turbine"]
    with pytest.raises(ValueError):
        CombinedCyclePlant(h_dict, "combined_cycle_plant")

    # Additional units not part of combined cycle plant
    h_dict["combined_cycle_plant"]["units"] = [
        "open_cycle_gas_turbine",
        "steam_turbine",
        "simple_battery",
    ]
    h_dict["combined_cycle_plant"]["simple_battery"] = copy.deepcopy(simple_battery)
    with pytest.raises(ValueError):
        CombinedCyclePlant(h_dict, "combined_cycle_plant")

    # Incorrect component type
    h_dict["combined_cycle_plant"]["units"] = ["open_cycle_gas_turbine", "steam_turbine"]
    h_dict["combined_cycle_plant"]["steam_turbine"]["component_type"] = "InvalidComponent"
    with pytest.raises(KeyError):
        CombinedCyclePlant(h_dict, "combined_cycle_plant")


def test_h_dict_structure():
    h_dict = copy.deepcopy(h_dict_combined_cycle_plant)

    tp = CombinedCyclePlant(h_dict, "combined_cycle_plant")

    # Check that the unit dicts were copied correctly (and generic names removed)
    assert "open_cycle_gas_turbine" not in h_dict["combined_cycle_plant"]
    assert "steam_turbine" not in h_dict["combined_cycle_plant"]
    assert "OCGT" in h_dict["combined_cycle_plant"]
    assert "ST" in h_dict["combined_cycle_plant"]
    assert h_dict["combined_cycle_plant"]["OCGT"]["component_type"] == "OpenCycleGasTurbine"
    assert h_dict["combined_cycle_plant"]["ST"]["component_type"] == "SteamTurbine"

    # Check that the initial conditions of units are copied correctly
    h_dict = tp.get_initial_conditions_and_meta_data(h_dict)
    assert h_dict["combined_cycle_plant"]["OCGT"]["power"] == 1000  # From initial conditions
    assert h_dict["combined_cycle_plant"]["ST"]["power"] == 1000  # From initial conditions

    # Check that combined cycle plant conditions are recorded correctly
    assert h_dict["combined_cycle_plant"]["power"] == 1000 + 1000

    print(h_dict["combined_cycle_plant"]["rated_capacity"])
    print(h_dict["combined_cycle_plant"]["ST"]["rated_capacity"])


def test_step():
    h_dict = copy.deepcopy(h_dict_combined_cycle_plant)

    tp = CombinedCyclePlant(h_dict, "combined_cycle_plant")

    # Provide power setpoints to the two units
    h_dict["combined_cycle_plant"]["power_setpoint"] = 500

    # Step the plant and check that power is updated correctly
    h_dict = tp.step(h_dict)
    power_ocgt = h_dict["combined_cycle_plant"]["OCGT"]["power"]
    power_steam = h_dict["combined_cycle_plant"]["ST"]["power"]

    assert power_ocgt < 1000  # Reacts to power setpoint
    assert power_steam < 1000  # Reacts to power setpoint

    # Total power computed correctly
    assert h_dict["combined_cycle_plant"]["power"] == power_ocgt + power_steam
