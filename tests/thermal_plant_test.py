import copy

import pytest
from hercules.plant_components.thermal_plant import ThermalPlant

from .test_inputs.h_dict import (
    h_dict_thermal_plant,
    simple_battery,
)


def test_init_from_dict():
    # Set up a system with one OCGT and one hard coal steam turbine.
    h_dict = copy.deepcopy(h_dict_thermal_plant)
    ThermalPlant(h_dict, "thermal_power_plant")


def test_invalid_unit_type():
    h_dict = copy.deepcopy(h_dict_thermal_plant)

    # Unspecified unit
    h_dict["thermal_power_plant"]["units"] = ["open_cycle_gas_turbine", "invalid_unit"]
    with pytest.raises(KeyError):
        ThermalPlant(h_dict, "thermal_power_plant")

    # Non thermal-type unit
    h_dict["thermal_power_plant"]["units"] = ["open_cycle_gas_turbine", "simple_battery"]
    h_dict["thermal_power_plant"]["simple_battery"] = copy.deepcopy(simple_battery)
    with pytest.raises(ValueError):
        ThermalPlant(h_dict, "thermal_power_plant")

    # Incorrect component type
    h_dict["thermal_power_plant"]["units"] = ["open_cycle_gas_turbine", "hard_coal_steam_turbine"]
    h_dict["thermal_power_plant"]["hard_coal_steam_turbine"]["component_type"] = "InvalidComponent"
    with pytest.raises(ValueError):
        ThermalPlant(h_dict, "thermal_power_plant")


def test_unit_copies():
    h_dict = copy.deepcopy(h_dict_thermal_plant)
    h_dict["thermal_power_plant"]["units"] = [
        "open_cycle_gas_turbine",
        "hard_coal_steam_turbine",
        "hard_coal_steam_turbine",
    ]

    # units and unit_names are unequal length
    with pytest.raises(ValueError):
        ThermalPlant(h_dict, "thermal_power_plant")

    # Update unit_names with non-unique values
    h_dict["thermal_power_plant"]["unit_names"] = ["OCGT1", "HST1", "HST1"]
    with pytest.raises(ValueError):
        ThermalPlant(h_dict, "thermal_power_plant")

    # Unique values
    h_dict["thermal_power_plant"]["unit_names"] = ["OCGT1", "HST1", "HST2"]
    tp = ThermalPlant(h_dict, "thermal_power_plant")

    # Check that there are three units of the correct types
    assert len(tp.units) == 3
    assert tp.units[0].component_type == "OpenCycleGasTurbine"
    assert tp.units[1].component_type == "HardCoalSteamTurbine"
    assert tp.units[2].component_type == "HardCoalSteamTurbine"


def test_h_dict_structure():
    h_dict = copy.deepcopy(h_dict_thermal_plant)

    tp = ThermalPlant(h_dict, "thermal_power_plant")

    # Check that the unit dicts were copied correctly (and generic names removed)
    assert "open_cycle_gas_turbine" not in h_dict["thermal_power_plant"]
    assert "hard_coal_steam_turbine" not in h_dict["thermal_power_plant"]
    assert "OCGT1" in h_dict["thermal_power_plant"]
    assert "HARD_COAL1" in h_dict["thermal_power_plant"]
    assert h_dict["thermal_power_plant"]["OCGT1"]["component_type"] == "OpenCycleGasTurbine"
    assert h_dict["thermal_power_plant"]["HARD_COAL1"]["component_type"] == "HardCoalSteamTurbine"

    # Check that the initial conditions of units are copied correctly
    h_dict = tp.get_initial_conditions_and_meta_data(h_dict)
    assert h_dict["thermal_power_plant"]["OCGT1"]["power"] == 1000  # From initial conditions
    assert h_dict["thermal_power_plant"]["HARD_COAL1"]["power"] == 1000  # From initial conditions
    assert h_dict["thermal_power_plant"]["OCGT1"]["rated_capacity"] == 1000
    assert h_dict["thermal_power_plant"]["HARD_COAL1"]["rated_capacity"] == 500000

    # Check that thermal plant conditions are recorded correctly
    assert h_dict["thermal_power_plant"]["power"] == 1000 + 1000
    assert h_dict["thermal_power_plant"]["rated_capacity"] == 500000 + 1000


def test_step():
    h_dict = copy.deepcopy(h_dict_thermal_plant)

    tp = ThermalPlant(h_dict, "thermal_power_plant")

    # Provide power setpoints to the two units
    h_dict["thermal_power_plant"]["power_setpoints"] = [800, 400000]

    # Step the plant and check that power is updated correctly
    h_dict = tp.step(h_dict)
    power_ocgt = h_dict["thermal_power_plant"]["OCGT1"]["power"]
    power_hard_coal = h_dict["thermal_power_plant"]["HARD_COAL1"]["power"]

    assert power_ocgt < 1000  # Reacts to power setpoint
    assert power_hard_coal < 500000  # Reacts to power setpoint

    # Total power computed correctly
    assert h_dict["thermal_power_plant"]["power"] == power_ocgt + power_hard_coal
