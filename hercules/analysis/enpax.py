"""Hand-off of one Hercules simulation to the ENPAX cost and ProFAST finance workflow.

Builds the case block (``plant`` and ``components``) from POI-limited energy, revenue and
component ratings. Collating cases and sites happens outside Hercules. Does not import
``enpax``.
"""
