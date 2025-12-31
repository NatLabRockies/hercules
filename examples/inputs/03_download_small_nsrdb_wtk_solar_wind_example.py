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

from hercules.resource.wind_solar_resource_downloader import (
    download_nsrdb_data,
    download_wtk_data,
)
from matplotlib import pyplot as plt

sys.path.append(".")


def run_small_example():
    """Run a small example with real data but limited time range and area"""

    # ARM Southern Great Plains coordinates
    target_lat = 36.607322
    target_lon = -97.487643
    year = 2020

    # Create data directory
    data_dir = "data/small_wtk_nsrdb_example"
    os.makedirs(data_dir, exist_ok=True)

    print("=" * 60)
    print("SMALL EXAMPLE: DOWNLOADING NSRDB DATA")
    print("=" * 60)

    # Download a small sample of NSRDB data with plotting
    try:
        nsrdb_data = download_nsrdb_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year,
            variables=["ghi"],  # Just one variable
            nsrdb_dataset_path="/nrel/nsrdb/conus",  # Demonstrating using a non-default dataset
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
    try:
        wtk_data = download_wtk_data(
            target_lat=target_lat,
            target_lon=target_lon,
            year=year,
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
