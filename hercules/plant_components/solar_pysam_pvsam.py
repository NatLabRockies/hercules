"""PVSam-based solar simulator using detailed PV model."""

import json
import sys

import numpy as np
import PySAM.Pvsamv1 as pvsam
from hercules.plant_components.solar_pysam_base import SolarPySAMBase
from hercules.utilities import hercules_float_type
from hercules.utilities_pvsam import size_electrical_parameters


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

        # Pre-compute the full power array for all time steps
        self._precompute_power_array()

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

    def _precompute_power_array(self):
        """Pre-compute the full power array for all time steps."""
        # Prepare solar resource data for all time steps
        solar_resource_data = {
            "tz": self.tz,  # 0 for UTC
            "elev": self.elev,
            "lat": self.lat,  # latitude
            "lon": self.lon,  # longitude
            "year": tuple(self.year_array),  # year array
            "month": tuple(self.month_array),  # month array
            "day": tuple(self.day_array),  # day array
            "hour": tuple(self.hour_array),  # hour array
            "minute": tuple(self.minute_array),  # minute array
            "dn": tuple(self.dni_array),  # direct normal irradiance array
            "df": tuple(self.dhi_array),  # diffuse irradiance array
            "gh": tuple(self.ghi_array),  # global horizontal irradiance array
            "wspd": tuple(self.wind_speed_array),  # windspeed array
            "tdry": tuple(self.temp_array),  # dry bulb temperature array
        }

        # Assign the full solar resource data
        self.system_model.SolarResource.assign({"solar_resource_data": solar_resource_data})
        self.system_model.AdjustmentFactors.assign({"constant": 0})

        # Apply dynamic sizing for the full simulation
        target_system_capacity = self.target_system_capacity
        target_ratio = self.target_dc_ac_ratio
        n_strings, n_combiners, n_inverters, calc_sys_capacity = size_electrical_parameters(
            self.system_model, target_system_capacity, target_ratio
        )

        # Execute the model once for all time steps
        self.system_model.execute()

        # Store the pre-computed power array (in kW)
        self.power_uncurtailed = np.array(self.system_model.Outputs.gen, dtype=hercules_float_type)

        # Store other outputs as arrays for efficient access
        self.dni_array_output = np.array(self.system_model.Outputs.dn, dtype=hercules_float_type)
        self.dhi_array_output = np.array(self.system_model.Outputs.df, dtype=hercules_float_type)
        self.ghi_array_output = np.array(self.system_model.Outputs.gh, dtype=hercules_float_type)
        self.aoi_array_output = np.array(
            self.system_model.Outputs.subarray1_aoi, dtype=hercules_float_type
        )
        self.poa_array_output = np.array(
            self.system_model.Outputs.subarray1_poa_eff, dtype=hercules_float_type
        )

    def _get_step_outputs(self, step):
        """Get the outputs for a specific step from pre-computed arrays.

        Args:
            step (int): Current simulation step.
        """
        # Extract outputs specific to PVSam model for this step
        self.dni = self.dni_array_output[step]  # direct normal irradiance
        self.dhi = self.dhi_array_output[step]  # diffuse horizontal irradiance
        self.ghi = self.ghi_array_output[step]  # global horizontal irradiance
        self.aoi = self.aoi_array_output[step]  # angle of incidence
        self.poa = self.poa_array_output[step]  # plane of array irradiance
