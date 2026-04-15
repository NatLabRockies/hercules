from importlib.metadata import version

__version__ = version("nlr-hercules")

from .hercules_model import HerculesModel
from .hercules_output import HerculesOutput
