"""
Small example using the real WTK/NSRDB downloader with minimal data.

Note that this example uses the download_nsrdb_data function, which requires an NLR API key that
can be obtained by visiting https://developer.nrel.gov/signup/. After receiving your API key, you
must make a configuration file at ~/.hscfg containing the following:

    hs_endpoint = https://developer.nrel.gov/api/hsds

    hs_api_key = YOUR_API_KEY_GOES_HERE

More information can be found at: https://github.com/NREL/hsds-examples.
"""

import os
import sys

import hercules.resource as resource
from matplotlib import pyplot as plt

sys.path.append(".")


def run_small_example():
    """Run a small example with real data but limited time range and area"""

    # ARM Southern Great Plains coordinates
    target_lat = 36.607322
    target_lon = -97.487643
    # Use 2022 for solar because the NSRDB TMY dataset only includes 2022-2024 data,
    #   and we want to demonstrate using a non-default dataset.
    year_solar = 2022

    # Create data directory
    data_dir = "data/small_wtk_nsrdb_example"
    os.makedirs(data_dir, exist_ok=True)

    print("=" * 60)
    print("SMALL EXAMPLE: DOWNLOADING NSRDB DATA")
    print("=" * 60)

    # Download a small sample of NSRDB data with plotting
    try:
        nsrdb_data = resource.nsrdb_downloader.download_nsrdb_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year_solar,
            variables=["ghi"],  # Just one variable
            nsrdb_dataset_path="/nrel/nsrdb/GOES/tmy/v4.0.0",  # Using a non-default dataset
            nsrdb_filename_prefix="nsrdb_tmy-",  # Downloading a typical meteorological year dataset
            coord_delta=0.05,  # Small area
            output_dir=data_dir,
            filename_prefix="nsrdb_small_example",
            plot_data=True,
            plot_type="timeseries",
        )

        if nsrdb_data:
            print("\n✓ Successfully downloaded NSRDB data!")
            for var, df in nsrdb_data.items():
                if var != "coordinates":
                    print(f"  {var}: {df.shape}")

    except Exception as e:
        print(f"✗ NSRDB download failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("SMALL EXAMPLE: DOWNLOADING WTK DATA")
    print("=" * 60)

    # Download a small sample of WTK data with plotting
    # Use 2020 for wind because WTK data is only avaialable 2018-2020
    year_wind = 2020

    try:
        wtk_data = resource.wtk_downloader.download_wtk_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year_wind,
            variables=["windspeed_100m"],  # Just one variable
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

        return True

    except Exception as e:
        print(f"✗ WTK download failed: {e}")
        return False


if __name__ == "__main__":
    print("Running small example with real NLR data...")
    print("This will download a small sample and create plots.")
    print("Note: This may take several minutes due to data download times.\n")

    success = run_small_example()

    if success:
        print("\n✓ Small example completed successfully!")
        print("\nThe script has demonstrated:")
        print("  - Real NLR data download (both NSRDB and WTK)")
        print("  - Time-series plotting")
        print("  - Spatial map plotting")
        print("  - Data saving in feather format")
        print("\nYou can now use the full script for larger datasets!")
    else:
        print("\n✗ Example failed. Check error messages above.")

    plt.show()
