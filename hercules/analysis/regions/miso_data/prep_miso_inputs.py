"""Prepare MISO inputs."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

MODULE_DIR = Path(__file__).resolve().parent
RAW_DATA_FOLDER = MODULE_DIR / "untracked_raw_files"
FIGURE_FOLDER = RAW_DATA_FOLDER / "figures"
MISO_LOAD_FOLDER = RAW_DATA_FOLDER / "load_forecast_and_actual"
OUTPUT_FEATHER = MODULE_DIR / "miso_daily_peak_hours.ftr"
LOCAL_HOUR_PNG = FIGURE_FOLDER / "peaks_by_local_hour.png"
UTC_HOUR_PNG = FIGURE_FOLDER / "peaks_by_utc_hour.png"

# MISO uses EST (fixed UTC-5, no DST) for all market reports, per a 2019 FERC
# ruling permitting MISO to use EST in the Day-Ahead market. This means every
# calendar day has exactly 24 HourEnding rows (1..24) with no DST gaps or
# duplicates. See gridstatus/gridstatus/miso.py for corroboration.
MISO_TZ = "EST"


def get_miso_daily_peaks() -> pd.DataFrame:
    """Extract the UTC start-of-hour of each day's peak MISO forecast load.

    Reads all ``*.xls`` files in ``untracked_raw_files/load_forecast_and_actual``,
    finds the hour with the highest MTLF (medium-term load forecast) per zone
    per local (EST) calendar day, saves a compact Feather file of UTC
    timestamps plus zone, prints summary statistics, and writes two peak-hour
    histograms (one in local EST time, one in UTC).

    Returns:
        Peaks DataFrame with columns ``time_utc`` (UTC-aware ``pd.Timestamp``,
        start of hour) and ``zone``.
    """
    # -- Step 1: Locate all yearly MISO DFAL history files. --
    files = sorted(MISO_LOAD_FOLDER.glob("*.xls"))
    if not files:
        raise FileNotFoundError(f"No .xls files found in {MISO_LOAD_FOLDER}")

    # -- Step 2: Read each xls into a long-format DataFrame and concatenate. --
    frames = []
    for path in files:
        raw = pd.read_excel(path, sheet_name=0, header=None)

        # Locate the first header row dynamically so we tolerate preamble
        # changes. The file also embeds repeated header rows throughout the
        # year, which get filtered by the ``dropna`` on parsed columns below.
        col0 = raw.iloc[:, 0].astype(str).str.strip()
        header_idx = int(col0[col0 == "MarketDay"].index[0])
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = raw.iloc[header_idx].tolist()
        df = df.loc[:, df.columns.notna()]

        df = df.rename(
            columns={
                "LoadResource Zone": "LoadResource",
                "MTLF (MWh)": "MTLF_MWh",
            }
        )
        df = df[["MarketDay", "HourEnding", "LoadResource", "MTLF_MWh"]]

        df["MarketDay"] = pd.to_datetime(df["MarketDay"], errors="coerce")
        df["HourEnding"] = pd.to_numeric(df["HourEnding"], errors="coerce")
        df["MTLF_MWh"] = pd.to_numeric(df["MTLF_MWh"], errors="coerce")
        df["LoadResource"] = df["LoadResource"].astype(str).str.strip()

        df = df.dropna(subset=["MarketDay", "HourEnding", "MTLF_MWh", "LoadResource"])
        df["HourEnding"] = df["HourEnding"].astype(int)
        frames.append(df.reset_index(drop=True))

    all_data = pd.concat(frames, ignore_index=True)
    all_data = all_data.drop_duplicates(
        subset=["MarketDay", "HourEnding", "LoadResource"], keep="first"
    )

    # -- Step 3: Convert HourEnding (1..24) to start-of-hour local EST time. --
    local_start = all_data["MarketDay"] + pd.to_timedelta(all_data["HourEnding"] - 1, unit="h")
    all_data["local_start"] = local_start.dt.tz_localize(MISO_TZ)

    # -- Step 4: For each (zone, local calendar day) find the row with the
    # peak MTLF and convert its start-of-hour timestamp to UTC. --
    peak_idx = all_data.groupby(["LoadResource", "MarketDay"])["MTLF_MWh"].idxmax()
    peaks = all_data.loc[peak_idx].copy()
    peaks["time_utc"] = peaks["local_start"].dt.tz_convert("UTC")
    peaks = peaks.rename(columns={"LoadResource": "zone"})
    peaks = peaks[["time_utc", "zone"]].sort_values(["zone", "time_utc"]).reset_index(drop=True)

    # -- Step 5: Save the peaks to a Feather file and print summary stats. --
    OUTPUT_FEATHER.parent.mkdir(parents=True, exist_ok=True)
    peaks.to_feather(OUTPUT_FEATHER)

    file_size_kb = OUTPUT_FEATHER.stat().st_size / 1024
    print(f"Saved {len(peaks):,} rows to {OUTPUT_FEATHER}")
    print(f"  first time_utc: {peaks['time_utc'].min()}")
    print(f"  last  time_utc: {peaks['time_utc'].max()}")
    print(f"  file size:      {file_size_kb:.1f} KB")
    print("  rows per zone:")
    for zone, count in peaks["zone"].value_counts().sort_index().items():
        print(f"    {zone:<12s} {count}")

    # Print the head of the dataframe for verification
    print("\nSample of the peaks dataframe:")
    print(peaks.head())

    # -- Step 6: Plot peak-hour histograms in local EST and UTC. --
    local_hour = peaks["time_utc"].dt.tz_convert(MISO_TZ).dt.hour
    utc_hour = peaks["time_utc"].dt.hour
    zones = sorted(peaks["zone"].unique())

    # Make the figure folder if it doesn't exist
    FIGURE_FOLDER.mkdir(parents=True, exist_ok=True)

    for hours, tz_label, out_path in [
        (local_hour, "EST (MISO local)", LOCAL_HOUR_PNG),
        (utc_hour, "UTC", UTC_HOUR_PNG),
    ]:
        counts = (
            pd.DataFrame({"zone": peaks["zone"], "hour": hours})
            .groupby(["zone", "hour"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=range(24), fill_value=0)
        )
        fig, ax = plt.subplots(figsize=(10, 5))
        for zone in zones:
            ax.plot(counts.columns, counts.loc[zone], marker="o", label=zone)
        ax.set_xlabel(f"Hour of day (start of hour, {tz_label})")
        ax.set_ylabel("# of daily peaks")
        ax.set_title(f"Distribution of MISO forecast daily peak hour ({tz_label})")
        ax.set_xticks(range(24))
        ax.legend(loc="upper left", fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        print(f"Wrote {out_path}")

    return peaks


if __name__ == "__main__":
    get_miso_daily_peaks()
