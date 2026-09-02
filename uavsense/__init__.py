"""
uavsense — physics library for distributed UAV formation RF sensing.

THIS PACKAGE IS COMPLETE AND TESTED. You do not edit it; you build on top of it.

    config.py      Scenario and URA parameter objects
    formations.py  formation geometry generators + transforms
    ura.py         the per-drone uniform rectangular array
    coarray.py     MIMO sum co-array and its metrics
    imaging.py     point spread function, quality metrics, coherent gain
    errors.py      position / phase error, dropped drones
    sequences.py   multi-snapshot strategies
    costs.py       reconfiguration time, coherence loss, Pareto front

The three calls your simulator makes most:

    from uavsense import BASE, get_formation, measure
    P = get_formation("square", 16, 40.0)
    m = measure([P], BASE)
    print(m)
"""

__version__ = "1.0.0"

from .config import BASE, Scenario, URA
from .formations import (
    get_formation, list_formations, valid_count, nearest_valid_count,
    FORMATION_REGISTRY, FORMATION_CONSTRAINTS,
)
from .imaging import point_spread_function, measure, coherent_gain, PSFMetrics
from .coarray import unique_coarray, fused_coarray, coarray_gain
from .sequences import build_sequence, SEQUENCE_STRATEGIES
from .ura import ura_pattern_cut, ura_pattern_grid

__all__ = [
    "BASE", "Scenario", "URA", "PSFMetrics",
    "get_formation", "list_formations", "valid_count", "nearest_valid_count",
    "FORMATION_REGISTRY", "FORMATION_CONSTRAINTS",
    "point_spread_function", "measure", "coherent_gain",
    "unique_coarray", "fused_coarray", "coarray_gain",
    "build_sequence", "SEQUENCE_STRATEGIES",
    "ura_pattern_cut", "ura_pattern_grid",
    "__version__",
]
