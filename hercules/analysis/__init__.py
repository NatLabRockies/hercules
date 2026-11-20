"""Post-processing analysis of a single Hercules simulation.

Public functions take one ``HerculesOutput`` as their first argument. Signals known during
the simulation are read from the logged output, never reconstructed. Columns added here are
prefixed ``analysis.``.
"""

from . import capacity_market, energy_market, enpax, plotting, regions, storage, utilities
