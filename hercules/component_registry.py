from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant
from hercules.plant_components.hard_coal_steam_turbine import HardCoalSteamTurbine
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
from hercules.plant_components.power_playback import PowerPlayback
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from hercules.plant_components.thermal_plant import ThermalPlant
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
    "ThermalPlant": ThermalPlant,
    "HardCoalSteamTurbine": HardCoalSteamTurbine,
    "PowerPlayback": PowerPlayback,
}

# Derived from registry keys for validation in utilities.py
VALID_COMPONENT_TYPES = tuple(COMPONENT_REGISTRY.keys())
