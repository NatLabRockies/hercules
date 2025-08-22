"""Plot wind and solar input data with shared time axes.

This script loads both wind_input.p and solar_input.p files and creates
comprehensive plots showing wind speeds, wind direction, and solar irradiance
components on shared time axes.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_wind_solar_data(
    wind_filename,
    solar_filename,
    num_wind_turbines_to_plot=5,
):
    """Plot wind and solar data with shared time axes.

    This function loads wind and solar data from pickle files and creates
    a comprehensive plot with three subplots: wind speeds, wind direction,
    and solar irradiance components.

    Args:
        wind_filename (str): Path to the wind input pickle file.
        solar_filename (str): Path to the solar input pickle file.
        num_wind_turbines_to_plot (int): Number of wind turbines to show
            (selects evenly spaced turbines from the total).

    """
    # Load the data
    print(f"Loading wind data from {wind_filename}...")
    wind_data = pd.read_pickle(wind_filename)

    print(f"Loading solar data from {solar_filename}...")
    solar_data = pd.read_pickle(solar_filename)

    # Create figure with subplots
    fig, axarr = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # Convert time to hours for better x-axis labels
    time_hours = wind_data["time"] / 60.0 / 60.0

    # Plot 1: Wind speeds for selected turbines
    print(f"Plotting wind speeds for {num_wind_turbines_to_plot} turbines...")

    # Find wind speed columns
    ws_columns = [col for col in wind_data.columns if col.startswith("ws_")]
    total_turbines = len(ws_columns)

    # Select evenly spaced turbines to plot
    turbine_indices = np.linspace(0, total_turbines - 1, num_wind_turbines_to_plot, dtype=int)

    for i, turbine_idx in enumerate(turbine_indices):
        col_name = f"ws_{turbine_idx:03d}"
        if col_name in wind_data.columns:
            axarr[0].plot(
                time_hours,
                wind_data[col_name],
                label=f"Turbine {turbine_idx}",
                alpha=0.7,
                linewidth=1,
            )

    axarr[0].set_ylabel("Wind Speed (m/s)")
    axarr[0].set_title("Wind Speeds for Selected Turbines")
    axarr[0].legend()
    axarr[0].grid(True, alpha=0.3)

    # Plot 2: Wind direction
    print("Plotting wind direction...")
    axarr[1].plot(time_hours, wind_data["wd_mean"], color="purple", linewidth=2)
    axarr[1].set_ylabel("Wind Direction (degrees)")
    axarr[1].set_title("Mean Wind Direction")
    axarr[1].grid(True, alpha=0.3)
    axarr[1].set_ylim(0, 360)

    # Plot 3: Solar irradiance components
    print("Plotting solar irradiance components...")

    # Plot GHI, DNI, and DHI
    axarr[2].plot(
        time_hours,
        solar_data["SRRL BMS Global Horizontal Irradiance (W/m²_irr)"],
        label="GHI",
        color="orange",
        linewidth=2,
    )
    axarr[2].plot(
        time_hours,
        solar_data["SRRL BMS Direct Normal Irradiance (W/m²_irr)"],
        label="DNI",
        color="red",
        linewidth=2,
    )
    axarr[2].plot(
        time_hours,
        solar_data["SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)"],
        label="DHI",
        color="blue",
        linewidth=2,
    )

    axarr[2].set_xlabel("Time (hours)")
    axarr[2].set_ylabel("Irradiance (W/m²)")
    axarr[2].set_title("Solar Irradiance Components")
    axarr[2].legend()
    axarr[2].grid(True, alpha=0.3)

    # Format x-axis
    axarr[2].set_xlim(0, 12)

    # Adjust layout
    plt.tight_layout()

    # Show the plot
    plt.show()

    # Print some statistics
    print("\nData Summary:")
    print(f"Wind data shape: {wind_data.shape}")
    print(f"Solar data shape: {solar_data.shape}")
    print(
        f"Time range: {wind_data['time'].min() / 60:.1f} - {wind_data['time'].max() / 60:.1f} hours"
    )
    print(f"Number of wind turbines: {total_turbines}")

    # Wind statistics
    ws_columns = [col for col in wind_data.columns if col.startswith("ws_")]
    if ws_columns:
        all_wind_speeds = wind_data[ws_columns].values.flatten()
        print(f"Wind speed range: {all_wind_speeds.min():.1f} to {all_wind_speeds.max():.1f} m/s")
        print(f"Mean wind speed: {all_wind_speeds.mean():.1f} m/s")

    # Solar statistics
    ghi_max = solar_data["SRRL BMS Global Horizontal Irradiance (W/m²_irr)"].max()
    print(f"Maximum GHI: {ghi_max:.1f} W/m²")


def main():
    """Load and plot wind and solar data."""
    print("Loading and plotting wind and solar data...")

    # Plot the data
    plot_wind_solar_data(
        wind_filename="inputs/wind_input.p",
        solar_filename="inputs/solar_input.p",
        num_wind_turbines_to_plot=5,
    )


if __name__ == "__main__":
    main()
