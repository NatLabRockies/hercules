# Python Simulators (Py_Sims)

The `PySims` class manages all Python-based simulation components in Hercules. It handles initialization, execution, and coordination of individual simulators while computing plant-level outputs.

## Overview

Py_Sims automatically detects and initializes components based on the [h_dict structure](h_dict.md). Each component is configured through its respective section in the h_dict (e.g., `wind_farm`, `solar_farm`, `battery`, `electrolyzer`).

## Available Components

| Component | Py_Sim Type | Description |
|-----------|-------------|-------------|
| `wind_farm` | `WindSimLongTerm` | FLORIS-based wind farm simulation |
| `solar_farm` | `SimpleSolar` | Basic solar model with efficiency |
| `solar_farm` | `SolarPySAM` | PySAM-based detailed solar simulation |
| `battery` | `SimpleBattery` | Basic battery storage model |
| `battery` | `LIB` | Detailed lithium-ion battery model |
| `electrolyzer` | `ElectrolyzerPlant` | Hydrogen production system |
