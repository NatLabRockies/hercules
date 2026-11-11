"""PVWatts-based solar simulator using simplified PV model."""

import numpy as np
import PySAM.Pvwattsv8 as pvwatts
from hercules.plant_components.solar_pysam_base import SolarPySAMBase
from hercules.utilities import hercules_float_type


class SolarPySAMPVWatts(SolarPySAMBase):
    """Solar simulator using PySAM's simplified PV model (Pvwattsv8)."""

    def __init__(self, h_dict, component_name):
        """Initialize the PVWatts solar simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
            component_name (str): Unique name for this instance (the YAML top-level key).
        """
        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

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

        # These values are always provided at the top level of the solar model input.
        top_level_dict = {
            "losses": h_dict[self.component_name]["losses"],
            "tilt": h_dict[self.component_name]["tilt"],
            "system_capacity": system_capacity,
        }
        top_level_set = set(top_level_dict.keys())

        # These values are the Hercules defaults for the PVWatts model and will be used if
        #   not provided in the PySAM options in the input.
        hercules_defaults = {
            "array_type": 3.0,  # single axis backtracking
            "azimuth": 180.0,
            "dc_ac_ratio": 1.0,
            "module_type": 0.0,  # standard crystalline silicon
        }

        # Check if any PySAM options for SystemDesign are provided in the input.
        if h_dict[self.component_name].get("pysam_options", {}).get("SystemDesign") is not None:
            pysam_options_set = set(h_dict[self.component_name]["pysam_options"]["SystemDesign"])
            self.logger.info(
                "PySAM model options provided in input are being used to define the PVWatts system."
            )
            common_keys = pysam_options_set.intersection(top_level_set)
            if len(common_keys) > 0:
                raise ValueError(
                    f"Error: The following parameters are provided in both the top-level input\
                        and the PySAM options: {common_keys}. Please remove these parameters\
                        from the PySAM options."
                )

        model_dict = (
            hercules_defaults
            | top_level_dict
            | h_dict[self.component_name].get("pysam_options", {}).get("SystemDesign", {})
        )

        self.model_params = {"SystemDesign": model_dict}
        self.capacity_rated = system_capacity / model_dict["dc_ac_ratio"]

    def _create_system_model(self):
        """Create and configure the PySAM system model."""
        # Create pysam model
        system_model = pvwatts.new()
        system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0

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
            "dn": tuple(self.DNI_array),  # direct normal irradiance array
            "df": tuple(self.DHI_array),  # diffuse irradiance array
            "gh": tuple(self.GHI_array),  # global horizontal irradiance array
            "wspd": tuple(self.wind_speed_array),  # windspeed array
            "tdry": tuple(self.temp_array),  # dry bulb temperature array
        }

        # Assign the full solar resource data
        self.system_model.SolarResource.assign({"solar_resource_data": solar_resource_data})

        # Execute the model once for all time steps
        self.system_model.execute()

        # Pull all outputs at the compute-grid resolution, with W -> kW for the
        # power channels. AC (post-inverter) and DC (pre-inverter) are
        # hypothetical power: the model output before any Hercules control
        # curtailment.
        compute_outputs = {
            "power_hypothetical": np.array(self.system_model.Outputs.ac, dtype=hercules_float_type)
            / hercules_float_type(1000.0),
            "DC_power_hypothetical": np.array(
                self.system_model.Outputs.dc, dtype=hercules_float_type
            )
            / hercules_float_type(1000.0),
            "DNI": np.array(self.system_model.Outputs.dn, dtype=hercules_float_type),
            "DHI": np.array(self.system_model.Outputs.df, dtype=hercules_float_type),
            "GHI": np.array(self.system_model.Outputs.gh, dtype=hercules_float_type),
            "AOI": np.array(self.system_model.Outputs.aoi, dtype=hercules_float_type),
            "POA": np.array(self.system_model.Outputs.poa, dtype=hercules_float_type),
        }

        # Upsample to the Hercules dt grid (no-op when compute_dt == dt).
        hercules_outputs = self._upsample_outputs_to_hercules_dt(compute_outputs)

        self.power_hypothetical_array = hercules_outputs["power_hypothetical"]
        self.DC_power_hypothetical_array = hercules_outputs["DC_power_hypothetical"]
        self.power_hypothetical = self.power_hypothetical_array[0]
        self.DC_power_hypothetical = self.DC_power_hypothetical_array[0]

        self.DNI_array_output = hercules_outputs["DNI"]
        self.DHI_array_output = hercules_outputs["DHI"]
        self.GHI_array_output = hercules_outputs["GHI"]
        self.AOI_array_output = hercules_outputs["AOI"]
        self.POA_array_output = hercules_outputs["POA"]

    def _get_step_outputs(self, step):
        """Get the outputs for a specific step from pre-computed arrays.

        Args:
            step (int): Current simulation step.
        """
        # Extract outputs specific to PVWatts model for this step
        self.DNI = self.DNI_array_output[step]  # direct normal irradiance
        self.DHI = self.DHI_array_output[step]  # diffuse horizontal irradiance
        self.GHI = self.GHI_array_output[step]  # global horizontal irradiance
        self.AOI = self.AOI_array_output[step]  # angle of incidence
        self.POA = self.POA_array_output[step]  # plane of array irradiance
