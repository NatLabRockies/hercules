"""PVSam-based solar simulator using detailed PV model."""

import json
import sys

import numpy as np
import PySAM.Pvsamv1 as pvsam
from hercules.plant_components.solar_pysam_base import SolarPySAMBase
from hercules.tools.Pvsamv1Tools import size_electrical_parameters


class SolarPySAMPVSam(SolarPySAMBase):
    """Solar simulator using PySAM's detailed PV model (Pvsamv1).

    This class implements the detailed photovoltaic model that calculates PV electrical
    output using separate module and inverter models. This model is more accurate but
    more time-intensive than PVWatts.
    """

    def __init__(self, h_dict):
        """Initialize the PVSam solar simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Store the type of this component
        self.component_type = "SolarPySAMPVSam"

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
        try:
            self.logger.info(
                "reading initial system info from {}".format(
                    h_dict[self.component_name]["system_info_file_name"]
                )
            )
            with open(h_dict[self.component_name]["system_info_file_name"], "r") as f:
                model_params = json.load(f)
            sys_design = {
                "ModelParams": model_params,
                "Other": {
                    "lat": h_dict[self.component_name]["lat"],
                    "lon": h_dict[self.component_name]["lon"],
                    "elev": h_dict[self.component_name]["elev"],
                },
            }

        except Exception:
            self.logger.info("Error: No PV system info json file specified for pvsam model.")
            sys.exit(1)  # exit program

            # TODO: use a default if none provided
            # sys_design = pvsam.default("FlatPlatePVSingleOwner")

        self.model_params = sys_design["ModelParams"]
        self.elev = sys_design["Other"]["elev"]
        self.lat = sys_design["Other"]["lat"]
        self.lon = sys_design["Other"]["lon"]

    def _create_system_model(self):
        """Create and configure the PySAM system model."""
        # Create pysam model
        system_model = pvsam.new()

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

        # Set parameters for pvsam model
        for k, v in self.model_params.items():
            try:
                system_model.value(k, v)
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                print(f"Warning: pysam error with parameter '{k}': {error_type} - {error_message}")
                print("Warning: continuing the simulation despite warning")

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

        # Dynamic sizing special treatment for pvsam model
        target_system_capacity = self.target_system_capacity
        target_ratio = self.target_dc_ac_ratio
        n_strings, n_combiners, n_inverters, calc_sys_capacity = size_electrical_parameters(
            self.system_model, target_system_capacity, target_ratio
        )

        self.system_model.execute()

        ac = np.array(self.system_model.Outputs.gen)  # in kW
        self.power = ac[0]  # calculating one timestep at a time
        if self.verbose:
            self.logger.info(f"self.power = {self.power}")

        # Apply control, if setpoint is provided
        P_setpoint = self._get_power_setpoint(h_dict)
        self.control(P_setpoint)

        if self.power < 0.0:
            self.power = 0.0

        # Extract outputs specific to PVSam model
        self.dni = self.system_model.Outputs.dn[0]  # direct normal irradiance
        self.dhi = self.system_model.Outputs.df[0]  # diffuse horizontal irradiance
        self.ghi = self.system_model.Outputs.gh[0]  # global horizontal irradiance
        self.aoi = self.system_model.Outputs.subarray1_aoi[0]  # angle of incidence
        self.poa = self.system_model.Outputs.subarray1_poa_eff[0]  # plane of array irradiance

        if self.verbose:
            self.logger.info(f"self.poa = {self.poa}")

        # Update the h_dict with outputs
        self._update_outputs(h_dict)

        return h_dict
