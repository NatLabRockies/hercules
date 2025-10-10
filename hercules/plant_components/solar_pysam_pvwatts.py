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

        # Pre-compute the full power array for all time steps
        self._precompute_power_array()

    def _setup_model_parameters(self, h_dict):
        """Set up the PV system model parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Set location parameters
        self.elev = h_dict[self.component_name]["elev"]
        self.lat = h_dict[self.component_name]["lat"]
        self.lon = h_dict[self.component_name]["lon"]

        # Use PVWatts system_capacity directly as documented
        # This represents the DC system capacity under Standard Test Conditions
        system_capacity = h_dict[self.component_name]["system_capacity"]  # (in kW)

        sys_design = {
            "ModelParams": {
                "SystemDesign": {
                    "array_type": 3.0,  # single axis backtracking
                    "azimuth": 180.0,
                    "dc_ac_ratio": 1.0,  # Force to 1.0
                    "losses": h_dict[self.component_name]["losses"],
                    "module_type": 0.0,  # standard crystalline silicon (hardcoded)
                    "system_capacity": system_capacity,
                    "tilt": h_dict[self.component_name]["tilt"],
                },
            },
        }

        self.model_params = sys_design["ModelParams"]

    def _create_system_model(self):
        """Create and configure the PySAM system model."""
        # Create pysam model
        system_model = pvwatts.new()
        system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

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

        # Execute the model once for all time steps
        self.system_model.execute()

        # Store the pre-computed power array (convert from W to kW)
        # Use DC power output directly from PVWatts
        self.power_uncurtailed = np.array(self.system_model.Outputs.dc) / 1000.0

        # Store other outputs as arrays for efficient access
        self.dni_array_output = np.array(self.system_model.Outputs.dn)
        self.dhi_array_output = np.array(self.system_model.Outputs.df)
        self.ghi_array_output = np.array(self.system_model.Outputs.gh)
        self.aoi_array_output = np.array(self.system_model.Outputs.aoi)
        self.poa_array_output = np.array(self.system_model.Outputs.poa)

    def _get_step_outputs(self, step):
        """Get the outputs for a specific step from pre-computed arrays.

        Args:
            step (int): Current simulation step.
        """
        # Extract outputs specific to PVWatts model for this step
        self.dni = self.dni_array_output[step]  # direct normal irradiance
        self.dhi = self.dhi_array_output[step]  # diffuse horizontal irradiance
        self.ghi = self.ghi_array_output[step]  # global horizontal irradiance
        self.aoi = self.aoi_array_output[step]  # angle of incidence
        self.poa = self.poa_array_output[step]  # plane of array irradiance
