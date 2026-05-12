# Units Convention in Hercules

Hercules follows a consistent units convention throughout the codebase to ensure clarity and prevent unit conversion errors.

## Power Units

**All power values in Hercules are specified in kilowatts (kW).**

This applies to:
- Component power ratings (e.g., wind turbine rated power)
- Battery charge/discharge rates
- Solar farm power output
- Electrolyzer power consumption
- Plant interconnect limits
- Power setpoints and references

## Energy Units

**All energy values in Hercules input/output interfaces are specified in kilowatt-hours (kWh).**

This applies to:
- Battery energy capacity (in input files and API)
- Energy storage results and outputs
- Cumulative energy production/consumption

### Internal Energy Calculations

While the external interface uses kWh, some components use different units internally for computational efficiency:

- **BatterySimple**: Uses kilojoules (kJ) for internal energy state calculations and converts to/from kWh at the interface boundaries using utility functions `kWh2kJ()` and `kJ2kWh()`
- **BatteryLithiumIon**: Uses kilowatt-hours (kWh) consistently throughout


## Output and Analysis

While internal calculations use kW/kWh, output plots and analysis may display results in MW/MWh for better readability when dealing with large-scale systems. This conversion is performed only at the presentation layer.

## Historical Note

Prior to this standardization, some components used MW/MWh units in their input specifications and performed internal conversions to kW/kWh. This approach has been deprecated to improve code clarity and maintainability.
