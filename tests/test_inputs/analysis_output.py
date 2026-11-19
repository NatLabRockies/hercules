"""Builder for small Hercules output files used by the ``hercules.analysis`` tests.

Analysis functions read a saved output file, so the analysis tests share this one builder
(an agreed exception to the no-fixtures rule). Data values stay inline in each test.
"""

import json

import h5py
import numpy as np
from hercules.hercules_output import HerculesOutput


def build_hercules_output(path, columns, h_dict, dt=60.0, starttime_utc=1704067200.0):
    """Write a minimal Hercules HDF5 output and return it as a ``HerculesOutput``.

    Args:
        path: Folder to write ``hercules_output.h5`` into (e.g. pytest ``tmp_path``).
        columns (dict): Logged columns by full name, e.g. ``{"battery.power": [...]}``.
            ``plant.power_bus`` defaults to the sum of ``<component>.power`` columns and
            ``plant.power_export`` to the bus power after ``efficiency_bus_to_poi``.
        h_dict (dict): Hercules input dictionary stored in the metadata.
        dt (float): Time step in s. Defaults to 60.
        starttime_utc (float): Start time as a Unix timestamp. Defaults to 2024-01-01.

    Returns:
        HerculesOutput: The written output.
    """
    columns = {name: np.asarray(values, dtype=float) for name, values in columns.items()}
    n = len(next(iter(columns.values())))
    component_power = [
        v for k, v in columns.items() if k.endswith(".power") and not k.startswith("plant.")
    ]
    bus = columns.get("plant.power_bus", np.sum(component_power, axis=0) + np.zeros(n))
    efficiency = h_dict.get("plant", {}).get("efficiency_bus_to_poi", 1.0)
    export = np.where(bus >= 0, bus * efficiency, bus / efficiency)
    export = columns.get("plant.power_export", export)

    filename = path / "hercules_output.h5"
    with h5py.File(filename, "w") as f:
        f["data/time"] = np.arange(n) * dt
        f["data/step"] = np.arange(n)
        f["data/plant_power_bus"] = bus
        f["data/plant_power_export"] = export
        f["data/plant_locally_generated_power"] = np.zeros(n)
        f.create_group("data/components")
        f.create_group("data/external_signals")
        for name, values in columns.items():
            if name.startswith("plant."):
                continue
            group = "external_signals" if name.startswith("external_signals.") else "components"
            f[f"data/{group}/{name}"] = values
        f.create_group("metadata")
        f["metadata"].attrs["h_dict"] = json.dumps(h_dict)
        f["metadata"].attrs["dt_sim"] = dt
        f["metadata"].attrs["total_simulation_time"] = n * dt
        f["metadata"].attrs["starttime_utc"] = starttime_utc
    return HerculesOutput(str(filename))
