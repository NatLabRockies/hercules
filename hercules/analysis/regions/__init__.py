"""Region-specific market data and rules.

Region data (zones, seasons, accreditation fractions, capacity prices) lives in a YAML file
per region (e.g. ``miso.yaml``), read with ``load_region``. Each region module (e.g.
``miso.py``) holds only rules for that region applied after the simulation.
"""

from . import miso
from .region_data import load_region
