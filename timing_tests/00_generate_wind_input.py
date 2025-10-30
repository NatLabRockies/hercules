"""Generate wind input data for 50 turbines with 1-minute time steps.

This script generates deterministic wind speed and direction data for 50 turbines
over a specified time period. The data is saved as a pickle file (.p) and is
designed to be reproducible across different machines.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_wind_input(
    num_turbines,
    num_time_steps,
    time_step_minutes,
    base_wind_speed,
    base_wind_direction,
    seed,
    output_filename,
):
    """Generate wind input data for multiple turbines.

    This function generates deterministic wind speed and direction data for multiple
    turbines over a specified time period. The data is saved as a pandas DataFrame
    to a pickle file (.p) and is designed to be reproducible across different machines.

    Args:
        num_turbines (int): Number of turbines to generate data for.
        num_time_steps (int): Number of time steps to generate.
        time_step_minutes (int): Time step in minutes.
        base_wind_speed (float): Base wind speed in m/s.
        base_wind_direction (float): Base wind direction in degrees.
        seed (int): Random seed for reproducibility.
        output_filename (str): Name of the output pickle file.

    """
    # Set random seed for reproducibility
    np.random.seed(seed)

    # Generate time arrays
    time_minutes = np.arange(num_time_steps) * time_step_minutes
    start_time = datetime(2020, 3, 1, 5, 0, 0)
    time_utc = [start_time + timedelta(minutes=int(t)) for t in time_minutes]

    # Generate base wind speed and direction using deterministic random walks
    ws_base = np.full(num_time_steps, base_wind_speed)
    wd_base = np.full(num_time_steps, base_wind_direction)

    # Add small perturbations to create realistic variation
    for i in range(1, num_time_steps):
        # Wind speed variation (smaller changes for more realistic data)
        ws_change = 0.05 * np.sin(i * 0.1) + 0.02 * np.random.randn()
        ws_base[i] = ws_base[i - 1] + ws_change

        # Wind direction variation (very small changes)
        wd_change = 0.5 * np.sin(i * 0.05) + 0.1 * np.random.randn()
        wd_base[i] = wd_base[i - 1] + wd_change

        # Apply bounds
        ws_base[i] = np.clip(ws_base[i], 5.0, 15.0)
        wd_base[i] = wd_base[i] % 360.0

    # Generate individual turbine wind speeds
    ws_data = np.zeros((num_time_steps, num_turbines))

    for turbine in range(num_turbines):
        # Each turbine gets the base wind speed plus turbine-specific variations
        turbine_offset = 0.2 * np.sin(turbine * 0.5)  # Systematic offset per turbine
        turbine_noise = 0.3 * np.random.randn(num_time_steps)  # Random noise

        # Add some spatial correlation (turbines closer together have more similar speeds)
        spatial_correlation = 0.1 * np.sin(turbine * 0.2 + time_minutes * 0.01)

        ws_data[:, turbine] = ws_base + turbine_offset + turbine_noise + spatial_correlation

        # Apply bounds to each turbine
        ws_data[:, turbine] = np.clip(ws_data[:, turbine], 5.0, 15.0)

    # Create the output dictionary
    wind_data = {
        "time_utc": time_utc,
        "wd_mean": wd_base,
    }

    # Convert to pandas dataframe
    df = pd.DataFrame(wind_data)

    # Add wind speed columns for each turbine
    for i in range(num_turbines):
        df[f"ws_{i:03d}"] = ws_data[:, i]

    # Save to pickle file
    df.to_pickle(output_filename)


def main():
    """Generate wind input data and save to pickle file."""
    print("Generating wind input data for 50 turbines...")

    # Generate the wind data
    generate_wind_input(
        num_turbines=50,
        num_time_steps=721,  # 12 hours
        time_step_minutes=1,
        base_wind_speed=10.0,
        base_wind_direction=270.0,
        seed=42,
        output_filename="inputs/wind_input.p",
    )


if __name__ == "__main__":
    main()
