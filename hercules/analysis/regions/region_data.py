"""Read region data YAML files."""

from pathlib import Path

import yaml


def load_region(name_or_path: str) -> dict:
    """Load region data from a built-in name (e.g. ``"miso"``) or a YAML file path.

    Paths under ``data_files`` are resolved relative to the YAML file.

    Args:
        name_or_path (str): Built-in region name or path to a region YAML file.

    Returns:
        dict: Region data.

    Raises:
        FileNotFoundError: If no YAML file is found.
    """
    path = Path(name_or_path)
    if path.suffix not in (".yaml", ".yml"):
        path = Path(__file__).parent / f"{str(name_or_path).lower()}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Region file '{path}' not found.")
    with open(path) as f:
        region = yaml.safe_load(f)
    region["data_files"] = {
        name: str((path.parent / filename).resolve())
        for name, filename in region.get("data_files", {}).items()
    }
    return region
