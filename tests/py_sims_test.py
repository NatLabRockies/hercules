from hercules import py_sims
from .test_inputs.h_dict import h_dict


def test_init_from_dict():
    # Test that a pysim can be initiated


    py_sims.PySims(h_dict)
