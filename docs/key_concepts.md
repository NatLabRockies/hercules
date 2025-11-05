# Key Concepts

Hercules is a modular simulation framework for hybrid plants.

## Core Components

### [H_Dict](h_dict.md)
The central data structure that contains all simulation parameters, component configurations, and runtime state. The h_dict serves as both the configuration interface and the runtime state container.

### [Hybrid Plant Components](hybrid_plant.md)
Manages individual components like wind farms, solar panels, batteries, and electrolyzers. 

### [HerculesModel](hercules_model.md)
The central orchestrator that drives the simulation forward step-by-step. HerculesModel manages the main execution loop, coordinates between components, and handles output generation.
