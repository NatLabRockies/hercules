"""Test to ensure version consistency between pyproject.toml and CITATION.cff."""

import re
from pathlib import Path


def read_version_from_pyproject():
    """Read version from pyproject.toml.

    Returns:
        str: Version string from pyproject.toml.
    """
    with open("pyproject.toml", "r") as f:
        content = f.read()

    # Use regex to find version line
    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    if not version_match:
        raise ValueError("Version not found in pyproject.toml")

    return version_match.group(1)


def read_version_from_citation():
    """Read version from CITATION.cff.

    Returns:
        str: Version string from CITATION.cff.
    """
    citation_file = Path("CITATION.cff")

    if not citation_file.exists():
        raise FileNotFoundError("CITATION.cff not found")

    with open(citation_file, "r") as f:
        for line in f:
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip()

    raise ValueError("Version not found in CITATION.cff")


def test_version_sync():
    """Test that versions in pyproject.toml and CITATION.cff match."""
    pyproject_version = read_version_from_pyproject()
    citation_version = read_version_from_citation()

    assert pyproject_version == citation_version, (
        f"Version mismatch: pyproject.toml has '{pyproject_version}' "
        f"but CITATION.cff has '{citation_version}'"
    )
