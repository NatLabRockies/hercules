# Example 07: Natural Gas Combustion Turbine (NGCT)

Demonstrates the `CombustionTurbineSimple` component with a 6-hour simulation (1-minute timesteps).

## Turbine Configuration

- **Capacity**: 100 MW
- **Minimum stable load fraction**: 20%
- **Heat rate**: 10,000 kJ/kWh
- **Ramp rates**: 500 kW/s (up/down)
- **Startup/shutdown time**: 1 hour each (default)

## Control Schedule

| Time (min) | Setpoint |
|------------|----------|
| 0–60 | Off |
| 60–120 | 100% |
| 120–180 | 50% |
| 180–210 | 10% (below min stable load) |
| 210–240 | 100% |
| 240+ | Shutdown |

## Running

```bash
python hercules_runscript.py
python plot_outputs.py
```
