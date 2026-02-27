"""Canonical definitions of Hercules component types.

This module defines the single source of truth for all valid
``component_type`` string values that can appear in Hercules input
files and in the HybridPlant component registry.
"""

# Canonical list of all supported component_type strings.
# When adding a new component, update this sequence and the
# _COMPONENT_REGISTRY in hybrid_plant to keep them aligned.
VALID_COMPONENT_TYPES = (
    "WindFarm",
    "WindFarmSCADAPower",
    "SolarPySAMPVWatts",
    "BatterySimple",
    "BatteryLithiumIon",
    "ElectrolyzerPlant",
    "OpenCycleGasTurbine",
)
