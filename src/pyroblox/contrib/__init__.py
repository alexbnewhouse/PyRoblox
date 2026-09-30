"""Social-network helpers with the call signatures of the 2.0 pre-release
(``pyroblox.contrib.edgelists`` and ``pyroblox.contrib.dataframes``).

They are thin wrappers over :mod:`pyroblox.collect`, which is where new code
should go.
"""

from . import dataframes, edgelists

__all__ = ["edgelists", "dataframes"]
