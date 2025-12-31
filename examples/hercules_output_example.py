"""Example demonstrating the HerculesOutput convenience class.

This example shows how to use the HerculesOutput class to easily access
Hercules simulation output data and metadata.
"""

import json
import os
import tempfile

import h5py
import numpy as np
from hercules import HerculesOutput


def create_example_hdf5_file(filename: str):
    """Create an example HDF5 file for demonstration.

    Args:
        filename (str): Path to the example file to create.
    """
    with h5py.File(filename, "w") as f:
        # Create basic data structure
        f.create_group("data")
        f.create_group("metadata")

        # Add time data (6 hours of simulation)
        time_steps = np.arange(0, 21600, 300)  # 5-minute intervals
        f["data/time"] = time_steps
        f["data/step"] = np.arange(len(time_steps))

        # Add plant data (simulated power output)
        plant_power = (
            100
            + 50 * np.sin(time_steps / 3600 * 2 * np.pi)
            + np.random.normal(0, 5, len(time_steps))
        )
        f["data/plant_power"] = plant_power
        f["data/plant_locally_generated_power"] = plant_power * 0.95

        # Add components group
        components_group = f.create_group("data/components")
        wind_power = (
            60
            + 30 * np.sin(time_steps / 3600 * 2 * np.pi)
            + np.random.normal(0, 3, len(time_steps))
        )
        solar_power = (
            40
            + 20 * np.sin(time_steps / 3600 * 2 * np.pi)
            + np.random.normal(0, 2, len(time_steps))
        )
        components_group["wind_farm.power"] = wind_power
        components_group["solar_farm.power"] = solar_power

        # Add external signals
        external_signals_group = f.create_group("data/external_signals")
        wind_speed = (
            8
            + 2 * np.sin(time_steps / 3600 * 2 * np.pi)
            + np.random.normal(0, 0.5, len(time_steps))
        )
        temperature = (
            20 + 5 * np.sin(time_steps / 3600 * 2 * np.pi) + np.random.normal(0, 1, len(time_steps))
        )
        external_signals_group["external_signals.wind_speed"] = wind_speed
        external_signals_group["external_signals.temperature"] = temperature

        # Add metadata
        f["metadata"].attrs["dt_sim"] = 1.0
        f["metadata"].attrs["dt_log"] = 300.0
        f["metadata"].attrs["log_every_n"] = 300
        f["metadata"].attrs["start_clock_time"] = 1234567890.0
        f["metadata"].attrs["end_clock_time"] = 1234567890.0 + 21600
        f["metadata"].attrs["starttime_utc"] = 1234567890.0  # Unix timestamp for UTC time
        f["metadata"].attrs["zero_time_utc"] = 1234567890.0

        # Add h_dict as JSON string
        example_h_dict = {
            "simulation": {"dt_sim": 1.0, "dt_log": 300.0, "t_final": 21600.0},
            "plant": {"name": "example_hybrid_plant", "components": ["wind_farm", "solar_farm"]},
            "wind_farm": {"type": "wind_meso_to_power", "capacity_mw": 100.0},
            "solar_farm": {"type": "solar_pysam_pvwatts", "capacity_mw": 50.0},
        }
        f["metadata"].attrs["h_dict"] = json.dumps(example_h_dict)


def main():
    """Demonstrate HerculesOutput usage."""
    print("HerculesOutput Example")
    print("=" * 50)

    # Create a temporary example file
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        # Create example data
        create_example_hdf5_file(temp_file)
        print(f"Created example file: {temp_file}")
        print()

        # Initialize HerculesOutput
        ho = HerculesOutput(temp_file)
        print(f"Initialized: {ho}")
        print()

        # Access metadata with dot notation
        print("Metadata Access:")
        print(f"  Simulation time step: {ho.dt_sim} seconds")
        print(f"  Logging time step: {ho.dt_log} seconds")
        print(f"  Log every N steps: {ho.log_every_n}")
        print(f"  Simulation duration: {ho.end_clock_time - ho.start_clock_time:.1f} seconds")
        print()

        # Print detailed metadata including UTC time information
        print("Detailed Metadata:")
        ho.print_metadata()
        print()

        # Access h_dict
        print("Simulation Configuration:")
        print(f"  Plant name: {ho.h_dict['plant']['name']}")
        print(f"  Components: {ho.h_dict['plant']['components']}")
        print(f"  Wind farm capacity: {ho.h_dict['wind_farm']['capacity_mw']} MW")
        print(f"  Solar farm capacity: {ho.h_dict['solar_farm']['capacity_mw']} MW")
        print()

        # Access data
        data = ho.df
        print("Data Access:")
        print(f"  Total time steps: {len(data)}")
        print(f"  Time range: {data['time'].min():.0f} to {data['time'].max():.0f} seconds")
        print(f"  Available columns: {list(data.columns)}")
        print()

        # Show some data statistics
        print("Data Statistics:")
        print(f"  Plant power - Mean: {data['plant.power'].mean():.1f} MW")
        print(f"  Plant power - Max: {data['plant.power'].max():.1f} MW")
        print(f"  Wind farm power - Mean: {data['wind_farm.power'].mean():.1f} MW")
        print(f"  Solar farm power - Mean: {data['solar_farm.power'].mean():.1f} MW")
        print(f"  Wind speed - Mean: {data['external_signals.wind_speed'].mean():.1f} m/s")
        print(f"  Temperature - Mean: {data['external_signals.temperature'].mean():.1f} °C")
        print()

        # Demonstrate subset functionality
        print("Subset Functionality:")

        # Get only wind and solar data
        subset = ho.get_subset(columns=["wind_farm.power", "solar_farm.power"])
        print(f"  Wind/solar subset columns: {list(subset.columns)}")

        # Get data for first hour only
        first_hour = ho.get_subset(time_range=(0, 3600))
        print(f"  First hour data points: {len(first_hour)}")

        # Get every 10th data point
        downsampled = ho.get_subset(stride=10)
        print(f"  Downsampled data points: {len(downsampled)}")
        print()

        print("Example completed successfully!")

    finally:
        # Clean up
        os.unlink(temp_file)


if __name__ == "__main__":
    main()
