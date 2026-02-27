"""Canonical definitions of Hercules component types.

This module defines the single source of truth for all valid
``component_type`` string values that can appear in Hercules input
files and in the HybridPlant component registry.
"""

from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from hercules.plant_components.wind_farm import WindFarm
from hercules.plant_components.wind_farm_scada_power import WindFarmSCADAPower

# Registry mapping component_type strings to their classes.
# Add new component types here to make them discoverable by HybridPlant.
COMPONENT_REGISTRY = {
    "WindFarm": WindFarm,
    "WindFarmSCADAPower": WindFarmSCADAPower,
    "SolarPySAMPVWatts": SolarPySAMPVWatts,
    "BatterySimple": BatterySimple,
    "BatteryLithiumIon": BatteryLithiumIon,
    "ElectrolyzerPlant": ElectrolyzerPlant,
    "OpenCycleGasTurbine": OpenCycleGasTurbine,
}

# Derived from registry keys for validation purposes
VALID_COMPONENT_TYPES = tuple(COMPONENT_REGISTRY.keys())
