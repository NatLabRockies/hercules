"""PVWatts-based solar simulator using simplified PV model."""

import numpy as np
import PySAM.Pvwattsv8 as pvwatts
from hercules.plant_components.solar_pysam_base import SolarPySAMBase


class SolarPySAMPVWatts(SolarPySAMBase):
    """Solar simulator using PySAM's simplified PV model (Pvwattsv8)."""

    def __init__(self, h_dict):
        """Initialize the PVWatts solar simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Store the type of this component
        self.component_type = "SolarPySAMPVWatts"

        # Call the base class init
        super().__init__(h_dict)

        # Set up PV system model parameters
        self._setup_model_parameters(h_dict)

        # Create and configure the PySAM model
        self._create_system_model()

    def _setup_model_parameters(self, h_dict):
        """Set up the PV system model parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        sys_design = {
            "ModelParams": {
                "SystemDesign": {
                    "array_type": 3.0,  # single axis backtracking
                    "azimuth": 180.0,
                    "dc_ac_ratio": h_dict[self.component_name]["target_dc_ac_ratio"],
                    "gcr": 0.29999999999999999,
                    "inv_eff": 96,
                    "losses": 14.075660688264469,
                    "module_type": 2.0,
                    "system_capacity": h_dict[self.component_name]["target_system_capacity"],
                    "tilt": 0.0,
                },
            },
            "Other": {
                "lat": h_dict[self.component_name]["lat"],
                "lon": h_dict[self.component_name]["lon"],
                "elev": h_dict[self.component_name]["elev"],
            },
        }

        self.model_params = sys_design["ModelParams"]
        self.elev = sys_design["Other"]["elev"]
        self.lat = sys_design["Other"]["lat"]
        self.lon = sys_design["Other"]["lon"]

    def _create_system_model(self):
        """Create and configure the PySAM system model."""
        # Create pysam model
        system_model = pvwatts.new()
        system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

        # Save the system model
        self.system_model = system_model

    def step(self, h_dict):
        """Execute one simulation step.

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary.
        """
        # Get the current step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Assign solar resource for this step
        self._assign_solar_resource(step)

        self.system_model.execute()

        ac = np.array(self.system_model.Outputs.gen)  # in kW
        self.power = ac[0]  # calculating one timestep at a time

        # Apply control
        self.control(h_dict[self.component_name]["power_setpoint"])

        if self.power < 0.0:
            self.power = 0.0

        if self.verbose:
            self.logger.info(f"self.power = {self.power}")

        # Extract outputs specific to PVWatts model
        self.dni = self.system_model.Outputs.dn[0]  # direct normal irradiance
        self.dhi = self.system_model.Outputs.df[0]  # diffuse horizontal irradiance
        self.ghi = self.system_model.Outputs.gh[0]  # global horizontal irradiance
        self.aoi = self.system_model.Outputs.aoi[0]  # angle of incidence
        self.poa = self.system_model.Outputs.poa[0]  # plane of array irradiance

        if self.verbose:
            self.logger.info(f"self.poa = {self.poa}")

        # Update the h_dict with outputs
        self._update_outputs(h_dict)

        return h_dict
