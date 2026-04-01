"""
Small example using the Open-Meteo downloader with minimal data
"""

import os
import sys

import numpy as np
from hercules.resource.openmeteo_downloader import download_openmeteo_data
from matplotlib import pyplot as plt

sys.path.append(".")


def run_small_example():
    """Run a small example with real data but limited time range and area"""

    # ARM Southern Great Plains coordinates
    target_lat = 36.607322
    target_lon = -97.487643
    year = 2023

    # Create data directory
    data_dir = "data/small_openmeteo_example"
    os.makedirs(data_dir, exist_ok=True)

    print("=" * 60)
    print("SMALL EXAMPLE: DOWNLOADING OPEN-METEO SOLAR DATA")
    print("=" * 60)

    # Download a small sample of Open-Meteo solar data with plotting for a single point at the
    # target coordinates. Note that data will be returned for the nearest weather grid point to
    # the requested coordinates.
    try:
        solar_data = download_openmeteo_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year,
            variables=["shortwave_radiation_instant"],  # Just one variable
            output_dir=data_dir,
            filename_prefix="openmeteo_small_example",
            plot_data=True,
            plot_type="timeseries",
        )

        if solar_data:
            print("\n✓ Successfully downloaded Open-Meteo solar data!")
            for var, df in solar_data.items():
                if var != "coordinates":
                    print(f"  {var}: {df.shape}")

    except Exception as e:
        print(f"✗ Open-Meteo solar download failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("SMALL EXAMPLE: DOWNLOADING OPEN-METEO WIND DATA")
    print("=" * 60)

    # Download a small sample of wind data with plotting for a grid of points

    # Define the grid of locations to download data for. Note that data will be returned for the
    # weather grid points nearest to the requested points and any duplicate points will be
    # excluded. The grid cell resolution varies with latitude, but at ~35 degrees latitude, the
    # grid cell resolution is approximately 0.027 degrees latitude (~2.4 km in the N-S direction)
    # and 0.0333 degrees longitude (~3.7km in the E-W direction).
    coord_delta = 0.05
    coord_resolution = 0.025

    target_lats = []
    target_lons = []

    for delta_lat in np.arange(-1 * coord_delta, coord_delta + coord_resolution, coord_resolution):
        for delta_lon in np.arange(
            -1 * coord_delta, coord_delta + coord_resolution, coord_resolution
        ):
            target_lats += [target_lat + delta_lat]
            target_lons += [target_lon + delta_lon]

    try:
        wind_data = download_openmeteo_data(
            target_lat=target_lats,
            target_lon=target_lons,
            year=year,
            variables=["wind_speed_80m"],  # Just one variable
            output_dir=data_dir,
            filename_prefix="openmeteo_small_example",
            plot_data=True,
            plot_type="map",
            remove_duplicate_coords=True,
        )

        if wind_data:
            print("\n✓ Successfully downloaded Open-Meteo wind data!")
            for var, df in wind_data.items():
                if var != "coordinates":
                    print(f"  {var}: {df.shape}")

            # Plot requested and actual coordinates
            print(
                "\nNote that the actual coordinates corresponding to the Open-Meteo data grid "
                "differ from the requested coordinates. Open-Meteo data is obtained at the "
                "nearest weather grid points to the requested coordinates."
            )

            plt.figure()
            plt.scatter(target_lons, target_lats, color="k", label="Requested Coordinates")
            plt.scatter(
                wind_data["coordinates"]["lon"],
                wind_data["coordinates"]["lat"],
                color="r",
                label="Actual Coordinates",
            )
            plt.axis("equal")
            plt.grid()
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")
            plt.title("Wind Data Coordinates")
            plt.legend()

        return True

    except Exception as e:
        print(f"✗ Open-Meteo wind download failed: {e}")
        return False


if __name__ == "__main__":
    print("Running small example with real Open-Meteo data...")
    print("This will download a small sample and create plots.")
    print("Note: This may take several minutes due to data download times.\n")

    success = run_small_example()

    if success:
        print("\n✓ Small example completed successfully!")
        print("\nThe script has demonstrated:")
        print("  - Real Open-Meteo data download (both solar and wind)")
        print("  - Time-series plotting")
        print("  - Spatial map plotting")
        print("  - Data saving in feather format")
        print("\nYou can now use the full script for larger datasets!")
    else:
        print("\n✗ Example failed. Check error messages above.")

    plt.show()
