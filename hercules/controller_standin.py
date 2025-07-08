from floris import FlorisModel


class ControllerStandin:
    """
    This class is a pass-through stand-in for a plant-level controller.
    Actual controllers should be implemented in WHOC
    (https://github.com/NREL/wind-hybrid-open-controller). However, this
    has been left in to allow users to run Hercules without plant-level
    control, if desired.

    Currently only does anything if wind_farm is present in the h_dict.
    """

    def __init__(self, h_dict):
        if "wind_farm" in h_dict:
            # Infer the number of turbines using the floris model
            floris_input_file = h_dict["wind_farm"]["floris_input_file"]
            fmodel = FlorisModel(floris_input_file)
            self.n_turbines = fmodel.n_turbines

    def step(self, h_dict):
        if "wind_farm" in h_dict:
            # Set deratings very high for now
            for t_idx in range(self.n_turbines):
                h_dict["wind_farm"][f"derating_{t_idx:03d}"] = 4000

            # Lower t0 derating every other 100 seconds
            if h_dict["time"] % 200 < 100:
                h_dict["wind_farm"]["derating_000"] = 500

        return h_dict
