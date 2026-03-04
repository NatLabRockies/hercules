# Adding a New Component

This guide explains how to add a new plant component type to Hercules. The process involves three steps:

1. Create the component class
2. Register the component
3. Document the component

## Step 1: Create the Component Class

Create a new Python file in `hercules/plant_components/` for your component. The class must:

- Inherit from `ComponentBase`
- Define a `component_category` class attribute
- Implement `__init__`, `step`, and `get_initial_conditions_and_meta_data` methods

### Minimal Example

```python
# hercules/plant_components/my_component.py

from hercules.plant_components.component_base import ComponentBase


class MyComponent(ComponentBase):
    """Brief description of the component."""

    component_category = "generator"  # or "storage" or "load"

    def __init__(self, h_dict, component_name):
        """Initialize the component.

        Args:
            h_dict: Dictionary containing simulation parameters.
            component_name: Unique name for this instance (the YAML key).
        """
        # Call base class init first
        super().__init__(h_dict, component_name)

        # Read component-specific parameters from h_dict
        self.rated_power = h_dict[self.component_name]["rated_power"]

        # Initialize internal state
        self.power = 0.0

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add initial conditions and metadata to h_dict.

        Called once during HybridPlant initialization.

        Args:
            h_dict: Dictionary containing simulation parameters.

        Returns:
            Updated h_dict with initial conditions.
        """
        h_dict[self.component_name]["power"] = self.power
        return h_dict

    def step(self, h_dict):
        """Advance the simulation by one time step.

        Args:
            h_dict: Dictionary containing current simulation state.

        Returns:
            Updated h_dict with component outputs.
        """
        # Read inputs (e.g., setpoint from controller)
        setpoint = h_dict[self.component_name].get("power_setpoint", 0.0)

        # Compute outputs
        self.power = min(setpoint, self.rated_power)

        # Write outputs to h_dict
        h_dict[self.component_name]["power"] = self.power

        return h_dict
```

### Key Requirements

| Requirement | Description |
|---|---|
| `component_category` | Must be `"generator"`, `"storage"`, or `"load"`. Generators contribute to `locally_generated_power`. |
| `super().__init__()` | Sets `self.component_name`, `self.component_type`, `self.dt`, `self.starttime`, and configures logging. |
| `power` output | All components must write a `power` value to `h_dict[self.component_name]["power"]` in the `step` method. |
| Return `h_dict` | Both `get_initial_conditions_and_meta_data` and `step` must return the modified `h_dict`. |

### Component Categories

- **`generator`**: Produces power (wind, solar, gas turbine). Power is summed into `locally_generated_power`.  Generator power should be positive signed to represent production.
- **`storage`**: Stores and releases power (batteries). Sign convention is automatically handled by `HybridPlant` in the following way.  It is assumed at the component model level, battery dischage is negatively signed.  At the plant level `HybridPlant` inverts the sign of the setpoint going into the battery component model, and inverts the power output coming out of the battery component model.  This way at the plant level, positive power represents discharge/production, consistent with the generator category.
- **`load`**: Consumes power (electrolyzers).  Power of loads should be negative signed to represent consumption.

While only generator power is included in `locally_generated_power`, all categories' power are combined into the total plant power in the `HybridPlant` class.

## Step 2: Register the Component

Add the component to `COMPONENT_REGISTRY` in `hercules/hybrid_plant.py` (see [Hybrid Plant Components](hybrid_plant.md)).


The key string (e.g., `"MyComponent"`) is the `component_type` value users will specify in their YAML input files.

## Testing

Add unit tests in `tests/my_component_test.py`. Test at minimum:

- Initialization with valid parameters
- `step` method produces expected outputs
- `get_initial_conditions_and_meta_data` sets initial state

Run tests with:

```bash
pytest tests/my_component_test.py -v
```

## Step 3: Document the Component

1. **Create a docs page**: Add `docs/my_component.md` with usage examples and parameter reference.

2. **Update the table of contents**: Add the page to `docs/_toc.yml` under "Plant Components":

   ```yaml
   - caption: Plant Components
     chapters:
     - file: wind
     - file: solar_pv
     # ...
     - file: my_component  # Add your page
   ```

3. **Update reference tables**: Add your component to the tables in:
   - [hybrid_plant.md](hybrid_plant.md) — Available Components table
   - [component_types.md](component_types.md) — Complete Component Type Reference table


## Summary Checklist

- [ ] Create `hercules/plant_components/my_component.py`
- [ ] Inherit from `ComponentBase`
- [ ] Define `component_category` class attribute
- [ ] Implement `__init__`, `step`, `get_initial_conditions_and_meta_data`
- [ ] Import and add to `COMPONENT_REGISTRY` in `hercules/hybrid_plant.py`
- [ ] Create tests in `tests/my_component_test.py`
- [ ] Create `docs/my_component.md`
- [ ] Add to `docs/_toc.yml`
- [ ] Update reference tables in `hybrid_plant.md` and `component_types.md`

