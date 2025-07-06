from hercules.controller_standin import ControllerStandin
from tests.test_inputs.h_dict import h_dict_wind

def test_step_sets_deratings_expected():
    """Test that ControllerStandin.step sets derating values as expected."""
    controller = ControllerStandin(h_dict_wind)
    test_dict = h_dict_wind.copy()
    test_dict["time"] = 50.0  # 50 % 200 < 100, so t0 should be 500
    result = controller.step(test_dict)
    assert result["wind_farm"]["derating_000"] == 500
    for t_idx in range(1, test_dict["wind_farm"]["num_turbines"]):
        assert result["wind_farm"][f"derating_{t_idx:03d}"] == 4000

def test_step_sets_all_4000_when_time_high():
    """Test that ControllerStandin.step sets all deratings to 4000 when time % 200 >= 100."""
    controller = ControllerStandin(h_dict_wind)
    test_dict = h_dict_wind.copy()
    test_dict["time"] = 150.0  # 150 % 200 = 150 >= 100, so all should be 4000
    result = controller.step(test_dict)
    for t_idx in range(test_dict["wind_farm"]["num_turbines"]):
        assert result["wind_farm"][f"derating_{t_idx:03d}"] == 4000 