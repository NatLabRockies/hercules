# Hybrid Plant Components

The `HybridPlant` class manages all plant components in Hercules. It handles initialization, execution, and coordination of individual components while computing plant-level outputs.

## Overview

HybridPlant automatically detects and initializes components based on the [h_dict structure](h_dict.md). Each component is configured through its respective section in the h_dict (e.g., `wind_farm`, `solar_farm`, `battery`, `electrolyzer`).

## Available Components

| Component | Component Type | Description |
|-----------|----------------|-------------|
| `wind_farm` | `WindSimLongTerm` | FLORIS-based wind farm simulation |
| `solar_farm` | `SolarPySAMPVSam` | PySAM-based detailed solar simulation |
| `solar_farm` | `SolarPySAMPVWatts` | PySAM-based simplified solar simulation |
| `battery` | `SimpleBattery` | Basic battery storage model |
| `battery` | `LIB` | Detailed lithium-ion battery model |
| `electrolyzer` | `ElectrolyzerPlant` | Hydrogen production system |
