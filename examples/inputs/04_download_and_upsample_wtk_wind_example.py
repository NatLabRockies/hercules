"""
Example using the real WTK downloader to download and and spatially and temporally upsample wind
speed and direction data.

Note that this example uses the download_wtk_data function, which requires an NLR API key that
can be obtained by visiting https://developer.nrel.gov/signup/. After receiving your API key, you
must make a configuration file at ~/.hscfg containing the following:

    hs_endpoint = https://developer.nrel.gov/api/hsds

    hs_api_key = YOUR_API_KEY_GOES_HERE

More information can be found at: https://github.com/NREL/hsds-examples.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import utm
from hercules.resource.upsample_wind_data import upsample_wind_data
from hercules.resource.wind_solar_resource_downloader import download_wtk_data
from matplotlib import pyplot as plt

sys.path.append(".")


def run_small_example():
    """Run a small example with real data but limited time range and area"""

    # ARM Southern Great Plains coordinates
    target_lat = 36.607322
    target_lon = -97.487643
    year = 2020

    # Create data directory
    data_dir = "data/wtk_upsample_example"
    os.makedirs(data_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("EXAMPLE: DOWNLOADING AND UPSAMPLING WTK DATA")
    print("=" * 60)

    # Download a sample of WTK wind speed and direction data with plotting
    try:
        wtk_data = download_wtk_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year,
            variables=["windspeed_100m", "winddirection_100m"],
            coord_delta=0.05,  # Small area
            output_dir=data_dir,
            filename_prefix="wtk_small_example",
            plot_data=True,
            plot_type="map",
        )

        if wtk_data:
            print("\n✓ Successfully downloaded WTK data!")
            for var, df in wtk_data.items():
                if var != "coordinates":
                    print(f"  {var}: {df.shape}")

    except Exception as e:
        print(f"✗ WTK download failed: {e}")
        return False

    # Spatially and temporally upsample the WTK wind speed and direction data at wind turbine
    # locations in a 2 x 3 array wind farm
    x_turbine_locs = np.array([-1500.0, 0.0, 1500.0, -1500.0, 0.0, 1500.0])
    y_turbine_locs = np.array([-1500.0, -1500.0, -1500.0, 1500.0, 1500.0, 1500.0])

    wtk_ws_data_filepath = Path(data_dir) / f"wtk_small_example_windspeed_100m_{year}.feather"
    wtk_wd_data_filepath = Path(data_dir) / f"wtk_small_example_winddirection_100m_{year}.feather"
    wtk_coords_filepath = Path(data_dir) / f"wtk_small_example_coords_{year}.feather"

    # Using downloaded WTK files, spatially interpolate wind speeds and directions at 6
    # turbine locations and upsample wind speeds by adding stochastic turbulence. The combined
    # upsampled dataframe will be saved in the same directory as the WTK files.
    #
    # The arguments turbulence_Uhub and turbulence_L are parameters used in the Kaimal
    # turbulence spectrum model
    #
    # Turbulence intensity is assigned as a function of wind speed based on the IEC normal
    # turbulence model such that a desired TI is achieved at a reference wind speed

    print("\nUpsampling raw WTK data...")

    df_upsample = upsample_wind_data(
        ws_data_filepath=wtk_ws_data_filepath,
        wd_data_filepath=wtk_wd_data_filepath,
        coords_filepath=wtk_coords_filepath,
        upsampled_data_dir=data_dir,
        upsampled_data_filename="wtk_small_example_upsample_6turbines.ftr",
        x_locs_upsample=x_turbine_locs,
        y_locs_upsample=y_turbine_locs,
        origin_lat=None,  # None sets the y origin to the mean latitude in the WTK files
        origin_lon=None,  # None sets the x origin to the mean longitude in the WTK files
        timestep_upsample=1,  # Upsample from 5-minute WTK resolution to 1-second resolution
        turbulence_Uhub=None,  # None sets turbulence_Uhub to the mean WTK wind speed
        turbulence_L=340.2,  # Default turbulence length scale defined in the IEC standard
        TI_ref=0.1,  # The desired TI corresponding to the reference wind speed TI_ws_ref
        TI_ws_ref=8.0,
        save_individual_wds=True,  # True saved wind directions for each upsampled location
    )

    # Load raw WTK wind speeds and locations
    df_wtk_ws = pd.read_feather(wtk_ws_data_filepath)
    df_wtk_coords = pd.read_feather(wtk_coords_filepath)

    # Convert WTK coordinates to easting and northing locations
    x_locs_wtk, y_locs_wtk, zone_number, zone_letter = utm.from_latlon(
        df_wtk_coords["lat"].values, df_wtk_coords["lon"].values
    )

    origin_lat = df_wtk_coords["lat"].mean()
    origin_lon = df_wtk_coords["lon"].mean()
    origin_x, origin_y, origin_zone_number, origin_zone_letter = utm.from_latlon(
        origin_lat, origin_lon
    )

    x_locs_wtk -= origin_x
    y_locs_wtk -= origin_y

    # Plot WTK grid points and upsampled turbine locations
    plt.figure()
    plt.scatter(x_locs_wtk, y_locs_wtk, label="WTK points")
    plt.scatter(x_turbine_locs, y_turbine_locs, color="r", label="Upsampled locations")
    for i in range(len(x_turbine_locs)):
        plt.text(x_turbine_locs[i] - 200.0, y_turbine_locs[i] + 175.0, i)
    plt.grid()
    plt.xlabel("Easting (m)")
    plt.ylabel("Northing (m)")
    plt.legend()
    plt.axis("equal")

    # Compare the upsampled wind speed at the first turbine location to the original WTK wind
    # speed at the nearest grid point for a single day (k can be 0 to 364)
    k = 1
    plt.figure(figsize=(9, 5))
    plt.plot(
        df_upsample["time_utc"][k * 60 * 60 * 24 : (k + 1) * 60 * 60 * 24],
        df_upsample["ws_000"][k * 60 * 60 * 24 : (k + 1) * 60 * 60 * 24],
        label="Upsampled wind speed at location 0",
    )
    plt.plot(
        df_wtk_ws["time_index"][k * 12 * 24 : (k + 1) * 12 * 24],
        df_wtk_ws["2279021"][k * 12 * 24 : (k + 1) * 12 * 24],
        label="WTK wind speed at nearest grid point",
    )
    plt.grid()
    plt.ylabel("Wind Speed (m/s)")
    plt.legend()

    return True


if __name__ == "__main__":
    print("Running small example with real NLR Wind Toolkit data...")
    print("This will download a small sample and create plots.")
    print("Next, the WTK data will be upsampled at 6 wind turbine locations.")
    print("Examples of the upsampled and original wind speed time series will be plotted.")
    print("Note: This may take several minutes due to data download times.\n")
    print("Also note that the upsampled wind file is approximately 2 GB.\n")

    success = run_small_example()

    if success:
        print("\n✓ Small example completed successfully!")
        print("\nThe script has demonstrated:")
        print("  - Real NLR WTK data download (both wind speed and direction)")
        print("  - Time-series plotting")
        print("  - Spatial map plotting")
        print("  - Data saving in feather format")
        print("  - Spatial interpolation and temporal upsampling with turbulence added")
        print("\nYou can now use the full script for larger datasets!")
    else:
        print("\n✗ Example failed. Check error messages above.")

    plt.show()
