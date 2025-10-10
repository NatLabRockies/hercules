"""HerculesOutput convenience class for reading Hercules HDF5 output files.

This module provides a convenient interface for reading Hercules simulation output files.
The HerculesOutput class allows easy access to both data and metadata with dot notation.
"""

import pandas as pd

from .utilities import get_hercules_metadata, read_hercules_hdf5


class HerculesOutput:
    """Convenience class for reading Hercules HDF5 output files.

    This class provides easy access to Hercules simulation output data and metadata.
    Users can still use the underlying utility functions directly if preferred.

    Args:
        filename (str): Path to Hercules HDF5 output file.

    Attributes:
        filename (str): Path to the output file.
        df (pd.DataFrame): Full simulation data.
        metadata (dict): Simulation metadata including h_dict and simulation info.
    """

    def __init__(self, filename: str):
        """Initialize HerculesOutput with a filename.

        Args:
            filename (str): Path to Hercules HDF5 output file.
        """
        self.filename = filename

        # Read metadata and data at initialization
        self.metadata = get_hercules_metadata(filename)
        self.df = read_hercules_hdf5(filename)

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
        print(f"   Time Step: {self.metadata.get('dt_log', 'Not available')} seconds")
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
        zero_time_utc = self.metadata.get("zero_time_utc")
        if zero_time_utc is not None:
            zero_time_utc = pd.to_datetime(zero_time_utc, unit="s", utc=True)
            print(f"   Zero Time (UTC): {zero_time_utc}")
        else:
            print("   Zero Time (UTC): Not available")
        start_time_utc = self.metadata.get("start_time_utc")
        if start_time_utc is not None:
            start_time_utc = pd.to_datetime(start_time_utc, unit="s", utc=True)
            print(f"   Start Time (UTC): {start_time_utc}")
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
            print("   Zero Time (UTC): Not available")
            print("   Start Time (UTC): Not available")
            print("   First Time (UTC): Not available")
            print("   Last Time (UTC): Not available")
            print("   Elapsed Calendar Time: Not available")

        print("Model Setup----")

        # Plant interconnect limit
        h_dict = self.metadata.get("h_dict", {})
        plant_config = h_dict.get("plant", {})
        interconnect_limit = plant_config.get("interconnect_limit", 0)
        if interconnect_limit > 0:
            print(f"   Interconnect Limit: {interconnect_limit / 1000:.1f} MW")
        else:
            print("   Interconnect Limit: Not available")

        # Wind farm information
        if "wind_farm" in h_dict:
            wind_config = h_dict["wind_farm"]
            n_turbines = wind_config.get("n_turbines", 0)
            rated_turbine_power = wind_config.get("rated_turbine_power", 0)
            if n_turbines > 0 and rated_turbine_power > 0:
                print(
                    f"   Wind Farm: {n_turbines} turbines @ "
                    f"{rated_turbine_power / 1000:.1f} MW each"
                )
                print(f"   Wind Farm Total: {n_turbines * rated_turbine_power / 1000:.1f} MW")
            else:
                print("   Wind Farm: Configuration incomplete")

        # Solar farm information
        if "solar_farm" in h_dict:
            solar_config = h_dict["solar_farm"]
            if "system_capacity" not in solar_config:
                raise KeyError(
                    "Missing required field 'system_capacity' in solar_farm configuration. "
                    "Please specify the DC system capacity of the solar farm in kW."
                )
            pv_capacity = solar_config["system_capacity"]
            print(f"   Solar Farm: {pv_capacity / 1000:.1f} MW")

        # Battery information
        if "battery" in h_dict:
            battery_config = h_dict["battery"]
            battery_capacity = battery_config.get("size", 0)
            if battery_capacity > 0:
                print(f"   Battery: {battery_capacity / 1000:.1f} MW")
            else:
                print("   Battery: Capacity not specified")

    def __repr__(self) -> str:
        """String representation of the HerculesOutput object.

        Returns:
            str: String representation showing filename and basic info.
        """
        return f"HerculesOutput(filename='{self.filename}')"
