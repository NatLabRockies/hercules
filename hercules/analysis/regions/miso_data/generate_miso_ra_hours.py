"""Convert the RA hour XLSX sheets provided by MISO into a sparse csv file of flagged hours.

All ``*.xlsx`` files in ``untracked_raw_files/`` (next to this script) are read
from their ``DATA`` tab and stitched together in time.  ``time_utc`` marks the
START of each hour.

The output csv file is written next to this script and tracked in the git repository.

To generate a new csv file using updated data, drop spreadsheets of RA data
into ``untracked_raw_files/``, run this script, then copy the printed coverage into
``RA_hours_coverage_utc`` and the file names into ``sources`` in ``miso.yaml``.

Output columns (one row per flagged hour, subregion and hour type):
    - ``time_utc``: hour-beginning UTC timestamp.
    - ``subregion``: ``central_north`` or ``south``.
    - ``hour_type``: ``RA`` (seasonal RA hour) or ``AAOC`` (annual RA hour).

Unlisted hours inside the coverage are not flagged. Season is not stored; it follows from
the date in MISO market time (EST), and the script checks this against the spreadsheets.
"""

from pathlib import Path

import pandas as pd

MODULE_DIR = Path(__file__).resolve().parent
INPUT_DIR = MODULE_DIR / "untracked_raw_files"
OUTPUT_PATH = MODULE_DIR / "miso_ra_hours.csv"

SEASONAL_CENTRAL_NORTH = "Seasonal RA Hour_RA Hour Identifier (Central + North)"
SEASONAL_SOUTH = "Seasonal RA Hour_RA Hour Identifier (South)"
AAOC_CENTRAL_NORTH = "Annual RA Hour (AAOC Hour)_RA Hour Identifier (Central + North)"
AAOC_SOUTH = "Annual RA Hour (AAOC Hour)_RA Hour Identifier (South)"


ONE_HOUR = pd.Timedelta(hours=1)


def _flatten_columns(cols):
    """Join the two header rows, dropping placeholder ``Unnamed:*`` levels."""
    return [
        "_".join(s for s in (str(x) for x in c) if not s.startswith("Unnamed")).strip("_")
        for c in cols
    ]


def _load_one(path):
    """Load one MISO RA-hour xlsx into a tidy per-file DataFrame."""
    raw = pd.read_excel(path, sheet_name="DATA", header=[0, 1])
    raw.columns = _flatten_columns(raw.columns)

    # timeest is hour-beginning EST with NO daylight-savings shifts (verified
    # empirically: every lookback year has perfectly uniform 1-hour spacing,
    # including leap years giving exactly 8784 rows).  Localize to fixed
    # UTC-5 (POSIX sign convention => "Etc/GMT+5") and convert to UTC.
    time_utc = raw["timeest"].dt.tz_localize("Etc/GMT+5").dt.tz_convert("UTC")

    out = pd.DataFrame(
        {
            "time_utc": time_utc,
            "season": raw["season"].astype("string"),
            "ra_central_north": raw[SEASONAL_CENTRAL_NORTH].astype("Int8"),
            "ra_south": raw[SEASONAL_SOUTH].astype("Int8"),
        }
    )
    if AAOC_CENTRAL_NORTH in raw.columns:
        # AAOC coverage is partial; nullable Int8 preserves NaN as empty
        # cells in the CSV (smaller than the legacy 1.0/0.0 floats).
        out["aaoc_central_north"] = raw[AAOC_CENTRAL_NORTH].astype("Int8")
        out["aaoc_south"] = raw[AAOC_SOUTH].astype("Int8")

    diffs = out["time_utc"].sort_values().diff().dropna().unique()
    assert len(diffs) == 1 and diffs[0] == ONE_HOUR, (
        f"{path.name}: irregular hour spacing (possible DST shift): {diffs}"
    )
    return out


def main():
    files = sorted(p for p in INPUT_DIR.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        raise FileNotFoundError(f"No .xlsx files found in {INPUT_DIR}")

    parts = [_load_one(f) for f in files]
    expected_rows = sum(len(p) for p in parts)

    df = pd.concat(parts, ignore_index=True).sort_values("time_utc").reset_index(drop=True)

    assert len(df) == expected_rows, f"row count mismatch: {len(df)} vs {expected_rows}"
    n_dupes = int(df["time_utc"].duplicated().sum())
    gap_diffs = df["time_utc"].diff().dropna()
    n_gaps = int((gap_diffs != ONE_HOUR).sum())

    print("Head:")
    print(df.head())
    print("\nTail:")
    print(df.tail())
    print(f"\nFiles read ({len(files)}):")
    for f in files:
        print(f"  {f.name}")
    print(f"\nRows: {len(df)} (expected {expected_rows})")
    print(f"Time range: {df['time_utc'].min()}  ->  {df['time_utc'].max()}")
    print(f"Duplicate timestamps: {n_dupes}")
    print(f"Gaps (non-1h diffs): {n_gaps}")
    print(f"Columns: {list(df.columns)}")
    print(f"Dtypes:\n{df.dtypes}")

    # Season must follow from the date in EST, as miso.yaml assumes (AI)
    local = df["time_utc"].dt.tz_convert("Etc/GMT+5")
    seasons = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring"}
    seasons |= {6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall"}
    assert (local.dt.month.map(seasons) == df["season"]).all(), "season not from the date"

    flags = [c for c in df.columns if c.startswith(("ra_", "aaoc_"))]
    sparse = df.melt(id_vars="time_utc", value_vars=flags).query("value == 1")
    sparse["hour_type"] = sparse["variable"].str.split("_").str[0].str.upper()
    sparse["subregion"] = sparse["variable"].str.split("_", n=1).str[1]
    sparse = sparse.sort_values(["time_utc", "subregion", "hour_type"])
    sparse[["time_utc", "subregion", "hour_type"]].to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(sparse)} flagged hours to {OUTPUT_PATH}")

    print("\nCoverage for miso.yaml (RA_hours_coverage_utc, [start, end)):")
    for hour_type, column in (("RA", "ra_south"), ("AAOC", "aaoc_south")):
        covered = df.loc[df[column].notna(), "time_utc"]
        print(
            f"  {hour_type}: ['{covered.min():%Y-%m-%dT%H:%M:%SZ}', "
            f"'{covered.max() + ONE_HOUR:%Y-%m-%dT%H:%M:%SZ}']"
        )


if __name__ == "__main__":
    main()
