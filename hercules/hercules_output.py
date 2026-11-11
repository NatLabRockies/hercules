"""HerculesOutput convenience class for reading Hercules HDF5 output files.

This module provides a convenient interface for reading Hercules simulation output files.
The HerculesOutput class allows easy access to both data and metadata with dot notation.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .utilities import get_hercules_metadata, read_hercules_hdf5


def _merge_controller_log(df: pd.DataFrame, controller_df: pd.DataFrame) -> pd.DataFrame:
    """Merge a controller log into the Hercules output DataFrame on ``time``.

    Array-valued signals are expanded to ``{col}.{i:03d}`` columns and all controller
    columns are prefixed with ``controller.``.

    Args:
        df (pd.DataFrame): Hercules output data with a ``time`` column (s).
        controller_df (pd.DataFrame): Controller log with a ``time`` column (s).

    Returns:
        pd.DataFrame: ``df`` with controller columns left-joined on ``time``.
    """
    if controller_df.empty or "time" not in controller_df.columns:
        return df

    controller_time = controller_df["time"]
    if df["time"].dtype == np.float32:
        controller_time = controller_time.astype(np.float32)
    columns = {"time": controller_time}
    for col in controller_df.columns.drop("time"):
        series = controller_df[col]
        is_array = series.map(lambda v: isinstance(v, (list, tuple, np.ndarray)))
        if is_array.any():
            expanded = pd.DataFrame(series[is_array].tolist(), index=series.index[is_array])
            for i in expanded.columns:
                columns[f"controller.{col}.{i:03d}"] = expanded[i].reindex(series.index)
        else:
            columns[f"controller.{col}"] = series

    return df.merge(pd.DataFrame(columns), on="time", how="left", validate="one_to_one")


class HerculesOutput:
    """Convenience class for reading Hercules HDF5 output files.

    This class provides easy access to Hercules simulation output data and metadata.
    Users can still use the underlying utility functions directly if preferred.

    If a controller log ``<stem>_controller_log.pkl`` exists next to the output file, its
    signals are merged into ``df`` as ``controller.*`` columns aligned on ``time``.

    Args:
        filename (str): Path to Hercules HDF5 output file.
        load_controller_log (bool): Whether to merge the controller log if present.
            Defaults to True.

    Attributes:
        filename (str): Path to the output file.
        df (pd.DataFrame): Full simulation data.
        metadata (dict): Simulation metadata including h_dict and simulation info.
    """

    def __init__(self, filename: str, load_controller_log: bool = True):
        """Initialize HerculesOutput with a filename.

        Args:
            filename (str): Path to Hercules HDF5 output file.
            load_controller_log (bool): Whether to merge the controller log if present.
                Defaults to True.
        """
        self.filename = filename

        # Read metadata and data at initialization
        self.metadata = get_hercules_metadata(filename)
        self.df = read_hercules_hdf5(filename)

        if load_controller_log:
            path = Path(filename)
            controller_log_file = path.with_name(path.stem + "_controller_log.pkl")
            if controller_log_file.exists():
                self.df = _merge_controller_log(self.df, pd.read_pickle(controller_log_file))

        # Make metadata attributes accessible via dot notation
        for key, value in self.metadata.items():
            setattr(self, key, value)

    def print_metadata(self):
        """Print detailed metadata about the simulation setup and performance.

        This method displays timing information, model configuration details,
        and system specifications in a formatted table.
        """
        print("Simulation Meta Data:")
        print("Time----")

        # Calculate total simulation time in a readable format
        total_simulation_time_s = self.metadata.get("total_simulation_time", 0)
        if total_simulation_time_s > 0:
            days = int(total_simulation_time_s // 86400)
            hours = int((total_simulation_time_s % 86400) // 3600)
            minutes = int((total_simulation_time_s % 3600) // 60)
            seconds = int(total_simulation_time_s % 60)
            time_str = f"{days} days {hours} hours {minutes} minutes {seconds} seconds"
        else:
            time_str = "Not available"

        print(f"  Total Simulation Time (seconds): {total_simulation_time_s}")
        print(f"   Total Simulation Time: {time_str}")
        print(f"   Time Step: {self.metadata.get('dt_sim', 'Not available')} seconds")
        print(f"   Num Steps: {len(self.df)}")

        # Wall time information
        total_time_wall = self.metadata.get("total_time_wall", 0)
        if total_time_wall > 0:
            print(f"   Elapsed Clock Time: {total_time_wall:.1f} seconds")
            if total_simulation_time_s > 0:
                simulation_rate = total_simulation_time_s / total_time_wall
                print(f"   Simulation Rate (x real time): {simulation_rate:.1f}x")
            else:
                print("   Simulation Rate (x real time): Not available")
        else:
            print("   Total Wall Time: Not available")
            print("   Simulation Rate (x real time): Not available")

        # UTC time information
        print("UTC Time----")

        # Backward compatibility: Try to read starttime_utc (new format)
        # or fall back to zero_time_utc (deprecated, from old output files)
        starttime_utc = self.metadata.get("starttime_utc")
        if starttime_utc is not None:
            starttime_utc = pd.to_datetime(starttime_utc, unit="s", utc=True)
            print(f"   Start Time (UTC): {starttime_utc}")
        else:
            # Backward compatibility: Check for deprecated zero_time_utc
            zero_time_utc = self.metadata.get("zero_time_utc")
            if zero_time_utc is not None:
                zero_time_utc = pd.to_datetime(zero_time_utc, unit="s", utc=True)
                print(f"   Start Time (UTC): {zero_time_utc} (from deprecated zero_time_utc)")
            else:
                print("   Start Time (UTC): Not available")

        # Check if time_utc column exists in the data
        if "time_utc" in self.df.columns:
            first_utc = self.df["time_utc"].iloc[0]
            last_utc = self.df["time_utc"].iloc[-1]
            print(f"   First Time (UTC): {first_utc}")
            print(f"   Last Time (UTC): {last_utc}")

            # Calculate elapsed calendar time
            if pd.notna(first_utc) and pd.notna(last_utc):
                elapsed_calendar = last_utc - first_utc
                elapsed_days = elapsed_calendar.days
                elapsed_hours = elapsed_calendar.seconds // 3600
                elapsed_minutes = (elapsed_calendar.seconds % 3600) // 60
                elapsed_seconds = elapsed_calendar.seconds % 60
                print(
                    f"   Elapsed Calendar Time: {elapsed_days} days {elapsed_hours} hours "
                    f"{elapsed_minutes} minutes {elapsed_seconds} seconds"
                )
            else:
                print("   Elapsed Calendar Time: Not available")
        else:
            print("   First Time (UTC): Not available (no time_utc column in data)")
            print("   Last Time (UTC): Not available (no time_utc column in data)")
            print("   Elapsed Calendar Time: Not available (no time_utc column in data)")

        print("Model Setup----")

        h_dict = self.metadata.get("h_dict", {})
        plant_config = h_dict.get("plant", {})
        interconnect_limit = plant_config.get("interconnect_limit", 0)
        if interconnect_limit > 0:
            print(f"   Interconnect Limit: {interconnect_limit / 1000:.1f} MW")
        else:
            print("   Interconnect Limit: Not available")
        print(f"   Bus to POI Efficiency: {plant_config.get('efficiency_bus_to_poi', 1.0)}")

        for name in h_dict.get("component_names", []):
            config = h_dict.get(name, {})
            component_type = config.get("component_type", "")
            if "turbine_count" in config and "turbine_power_rated" in config:
                print(
                    f"   {name} ({component_type}): {config['turbine_count']} turbines @ "
                    f"{config['turbine_power_rated'] / 1000:.1f} MW each"
                )
            elif "DC_capacity_rated" in config:
                print(
                    f"   {name} ({component_type}): {config['capacity_rated'] / 1000:.1f} MW AC, "
                    f"{config['DC_capacity_rated'] / 1000:.1f} MW DC"
                )
            elif "energy_capacity" in config:
                print(
                    f"   {name} ({component_type}): {config['energy_capacity'] / 1000:.1f} MWh, "
                    f"{config.get('power_discharge_max', 0) / 1000:.1f} MW discharge"
                )
            elif "capacity_rated" in config:
                print(f"   {name} ({component_type}): {config['capacity_rated'] / 1000:.1f} MW")
            else:
                print(f"   {name} ({component_type})")

    def __repr__(self) -> str:
        """String representation of the HerculesOutput object.

        Returns:
            str: String representation showing filename and basic info.
        """
        return f"HerculesOutput(filename='{self.filename}')"
