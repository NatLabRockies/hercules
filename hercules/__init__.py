from importlib.metadata import version

__version__ = version("nlr-hercules")

from pathlib import Path

from .hercules_model import HerculesModel
from .hercules_output import HerculesOutput

HERCULES_ROOT_DIR = Path(__file__).resolve().parent
HERCULES_EXAMPLE_DIR = HERCULES_ROOT_DIR.parent / "examples"
