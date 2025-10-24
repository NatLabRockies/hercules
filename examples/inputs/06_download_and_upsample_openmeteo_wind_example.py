"""
Example using the Open-Meteo downloader to download and and spatially and temporally upsample wind
speed and direction data
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import utm
from hercules.resource.upsample_wind_data import upsample_wind_data
from hercules.resource.wind_solar_resource_downloader import (
    download_openmeteo_data,
)
from matplotlib import pyplot as plt

sys.path.append(".")


def run_small_example():
    """Run a small example with real data but limited time range and area"""

    # ARM Southern Great Plains coordinates
    target_lat = 36.607322
    target_lon = -97.487643
    year = 2023

    # Create data directory
    data_dir = "data/openmeteo_upsample_example"
    os.makedirs(data_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("EXAMPLE: DOWNLOADING AND UPSAMPLING OPEN-METEO WIND DATA")
    print("=" * 60)

    # Download a sample of Open-Meteo wind speed and direction data with plotting

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
            variables=["windspeed_80m", "winddirection_80m"],
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

    except Exception as e:
        print(f"✗ Open-Meteo download failed: {e}")
        return False

    # Spatially and temporally upsample the Open-Meteo wind speed and direction data at wind
    # turbine locations in a 2 x 3 array wind farm
    x_turbine_locs = np.array([-2500.0, 0.0, 2500.0, -2500.0, 0.0, 2500.0])
    y_turbine_locs = np.array([-1500.0, -1500.0, -1500.0, 1500.0, 1500.0, 1500.0])

    openmeteo_ws_data_filepath = (
        Path(data_dir) / f"openmeteo_small_example_windspeed_80m_{year}.feather"
    )
    openmeteo_wd_data_filepath = (
        Path(data_dir) / f"openmeteo_small_example_winddirection_80m_{year}.feather"
    )
    openmeteo_coords_filepath = Path(data_dir) / f"openmeteo_small_example_coords_{year}.feather"

    # Using downloaded Open-Meteo wind files, spatially interpolate wind speeds and directions
    # and at 6 turbine locations and upsample wind speeds by adding stochastic turbulence. The
    # combined upsampled dataframe will be saved in the same directory as the Open-Meteo files.
    #
    # The arguments turbulence_Uhub and turbulence_L are parameters used in the Kaimal
    # turbulence spectrum model
    #
    # Turbulence intensity is assigned as a function of wind speed based on the IEC normal
    # turbulence model such that a desired TI is achieved at a reference wind speed

    print("\nUpsampling raw Open-Meteo data...")

    df_upsample = upsample_wind_data(
        ws_data_filepath=openmeteo_ws_data_filepath,
        wd_data_filepath=openmeteo_wd_data_filepath,
        coords_filepath=openmeteo_coords_filepath,
        upsampled_data_dir=data_dir,
        upsampled_data_filename="openmeteo_small_example_upsample_6turbines.ftr",
        x_locs_upsample=x_turbine_locs,
        y_locs_upsample=y_turbine_locs,
        origin_lat=None,  # None sets the y origin to the mean latitude in the Open-Meteo files
        origin_lon=None,  # None sets the x origin to the mean longitude in the Open-Meteo files
        timestep_upsample=1,  # Upsample from 15-minute Open-Meteo resolution to 1-second res.
        turbulence_Uhub=None,  # None sets turbulence_Uhub to the mean Open-Meteo wind speed
        turbulence_L=340.2,  # Default turbulence length scale defined in the IEC standard
        TI_ref=0.1,  # The desired TI corresponding to the reference wind speed TI_ws_ref
        TI_ws_ref=8.0,
        save_individual_wds=True,  # True saved wind directions for each upsampled location
    )

    # Load raw Open-Meteo wind speeds and locations
    df_openmeteo_ws = pd.read_feather(openmeteo_ws_data_filepath)
    df_openmeteo_coords = pd.read_feather(openmeteo_coords_filepath)

    # Convert Open-Meteo coordinates to easting and northing locations
    x_locs_openmeteo, y_locs_openmeteo, zone_number, zone_letter = utm.from_latlon(
        df_openmeteo_coords["lat"].values, df_openmeteo_coords["lon"].values
    )

    origin_lat = df_openmeteo_coords["lat"].mean()
    origin_lon = df_openmeteo_coords["lon"].mean()
    origin_x, origin_y, origin_zone_number, origin_zone_letter = utm.from_latlon(
        origin_lat, origin_lon
    )

    x_locs_openmeteo -= origin_x
    y_locs_openmeteo -= origin_y

    # Plot Open-Meteo grid points and upsampled turbine locations
    plt.figure()
    plt.scatter(x_locs_openmeteo, y_locs_openmeteo, label="Open-Meteo points")
    plt.scatter(x_turbine_locs, y_turbine_locs, color="r", label="Upsampled locations")
    for i in range(len(x_turbine_locs)):
        plt.text(x_turbine_locs[i] - 200.0, y_turbine_locs[i] + 175.0, i)
    plt.grid()
    plt.xlabel("Easting (m)")
    plt.ylabel("Northing (m)")
    plt.legend()
    plt.axis("equal")

    # Compare the upsampled wind speed at the first turbine location to the original
    # Open-Meteo wind speed at the nearest grid point for a single day (k can be 0 to 364)
    k = 1
    plt.figure(figsize=(9, 5))
    plt.plot(
        df_upsample["time_utc"][k * 60 * 60 * 24 : (k + 1) * 60 * 60 * 24],
        df_upsample["ws_000"][k * 60 * 60 * 24 : (k + 1) * 60 * 60 * 24],
        label="Upsampled wind speed at location 0",
    )
    plt.plot(
        df_openmeteo_ws["time_index"][k * 4 * 24 : (k + 1) * 4 * 24],
        df_openmeteo_ws["9"][k * 4 * 24 : (k + 1) * 4 * 24],
        label="Open-Meteo wind speed at nearest grid point",
    )
    plt.grid()
    plt.ylabel("Wind Speed (m/s)")
    plt.legend()

    return True


if __name__ == "__main__":
    print("Running small example with real Open-Meteo wind data...")
    print("This will download a small sample and create plots.")
    print("Next, the Open-Meteo data will be upsampled at 6 wind turbine locations.")
    print("Examples of the upsampled and original wind speed time series will be plotted.")
    print("Note: This may take several minutes due to data download times.\n")
    print("Also note that the upsampled wind file is approximately 2 GB.\n")

    success = run_small_example()

    if success:
        print("\n✓ Small example completed successfully!")
        print("\nThe script has demonstrated:")
        print("  - Real Open-Meteo wind data download (both wind speed and direction)")
        print("  - Time-series plotting")
        print("  - Spatial map plotting")
        print("  - Data saving in feather format")
        print("  - Spatial interpolation and temporal upsampling with turbulence added")
        print("\nYou can now use the full script for larger datasets!")
    else:
        print("\n✗ Example failed. Check error messages above.")

    plt.show()
