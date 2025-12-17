import copy

from hercules.plant_components.combustion_turbine_simple import CombustionTurbineSimple

from .test_inputs.h_dict import (
    h_dict_combustion_turbine,
)


def test_init_from_dict():
    """Test that CombustionTurbineSimple can be initialized from a dictionary."""
    ct = CombustionTurbineSimple(copy.deepcopy(h_dict_combustion_turbine))
    assert ct is not None
