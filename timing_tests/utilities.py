"""Utilities for recording and managing timing test results."""

import csv
import os
import platform
import subprocess
from datetime import datetime
from typing import Optional


def record_timing_result(
    result_file: str,
    test_name: str,
    test_result_seconds: float,
    notes: Optional[str] = None,
) -> None:
    """Record the result of a timing test to a CSV file.

    This function opens (creates or appends to) a CSV file and adds a row with the
    provided test information along with automatically collected metadata including
    commit hash, branch name, date/time, and CPU information.

    Args:
        result_file (str): Path to the CSV file to write results to. Must have .csv extension.
        test_name (str): Name of the test that was executed.
        test_result_seconds (float): Test execution time in seconds.
        notes (str, optional): Additional notes about the test run. Defaults to None.

    Raises:
        ValueError: If result_file doesn't end with .csv extension.
        subprocess.CalledProcessError: If git commands fail to execute.
    """
    if not result_file.endswith(".csv"):
        raise ValueError("Result file must have .csv extension")

    # Collect metadata
    metadata = _collect_metadata()

    # Prepare row data
    row_data = {
        "test_name": test_name,
        "test_result_seconds": test_result_seconds,
        "notes": notes or "",
        "commit_hash": metadata["commit_hash"],
        "branch": metadata["branch"],
        "date_time": metadata["date_time"],
        "cpu": metadata["cpu"],
    }

    # Write to CSV
    _write_csv_row(result_file, row_data)


def _collect_metadata() -> dict:
    """Collect metadata about the current environment and git state.

    Returns:
        dict: Dictionary containing commit hash, branch, date/time, and CPU info.
    """
    metadata = {}

    # Get git information
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        metadata["commit_hash"] = commit_hash[:8]  # Short hash
    except (subprocess.CalledProcessError, FileNotFoundError):
        metadata["commit_hash"] = "unknown"

    try:
        # Get branch name
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        metadata["branch"] = branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        metadata["branch"] = "unknown"

    # Get current date/time
    metadata["date_time"] = datetime.now().isoformat()

    # Get CPU information
    metadata["cpu"] = platform.processor() or platform.machine()

    return metadata


def _write_csv_row(filename: str, row_data: dict) -> None:
    """Write a row to a CSV file, creating the file if it doesn't exist.

    Args:
        filename (str): Path to the CSV file.
        row_data (dict): Dictionary containing the row data to write.
    """
    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = list(row_data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header if file is new
        if not file_exists:
            writer.writeheader()

        # Write the row
        writer.writerow(row_data)
