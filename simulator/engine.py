"""
The compute layer — turns a SimConfig into a Result, and does it fast enough.

============================================================================
YOU BUILD THIS.
============================================================================

WHAT THIS LAYER IS FOR
----------------------
The GUI must never call `uavsense` directly. It calls `run(config)` and gets a
`Result` back. Everything awkward lives here:

    - building the snapshot sequence from the strategy
    - applying errors
    - applying coherence weights
    - caching, so dragging a slider back to a previous value is instant
    - a preview mode, so the app stays responsive while a slider is moving

WHY CACHING IS NOT OPTIONAL
---------------------------
Streamlit re-runs your whole script top to bottom on EVERY widget interaction.
Type one character in a text box and the script runs again. Without a cache, a
full PSF runs on every keystroke and the app feels broken.

With a cache keyed on `config.cache_key()`, only a change that actually affects
the physics costs anything. This is the single biggest difference between a
simulator that feels good and one that feels awful, and it is why `cache_key`
excludes the label.

THE TWO-TIER TRICK
------------------
Cost scales with grid_points SQUARED, so the grid is the one dial that really
changes how the app feels. Measured here, one snapshot with 16 drones:

    101 x 101     ~20 ms      genuinely interactive
    201 x 201     ~65 ms      the default; comfortable
    301 x 301    ~155 ms
    401 x 401    ~295 ms      export quality

The useful fact: metrics agree to about 1% across that whole range. The extra
samples only smooth the picture. So a coarse preview is not an approximation you
are apologising for — the numbers are the same.

    preview  (101x101)  while the user is dragging
    default  (201x201)  once they stop
    fine     (401x401)  only for an exported figure

Those are for the PSF alone. `measure()` computes it AGAIN, so a naive `run()`
doubles every number above — which is the trap flagged in (W03-3).

Build `run(config, preview=True/False)` around that from the start; retrofitting
it later means touching every call site.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable
from time import perf_counter

import numpy as np

from uavsense.config import Scenario
from uavsense.imaging import PSFMetrics, point_spread_function, measure
from uavsense.formations import get_formation
from uavsense.errors import apply_errors
from uavsense.sequences import build_sequence
from uavsense.costs import sequence_weights
from uavsense.coarray import fused_coarray, coarray_gain

from .state import SimConfig, ValidationError, Scenario

__all__ = ["Result", "run", "build_snapshots", "clear_cache", "cache_stats",
           "estimate_cost"]


@dataclass
class Result:
    """
    Everything one run produced. Given — do not change the field list, because
    the plotting and export modules are written against it.
    """

    config: SimConfig
    scenario: Scenario

    snapshots: list[np.ndarray]      # actual drone positions used, per snapshot
    nominal: list[np.ndarray]        # positions the beamformer assumed
    weights: list[float]             # per-snapshot combining weights
    morph_times: list[float]         # cumulative reconfiguration time [s]

    axis: np.ndarray                 # (G,) ground coordinates [m]
    image: np.ndarray                # (G, G) normalised PSF magnitude
    metrics: PSFMetrics

    coarray: np.ndarray              # (M, 2) fused unique co-array points
    coarray_gain: float              # fused points / single-snapshot points

    compute_ms: float = 0.0
    from_cache: bool = False
    preview: bool = False

    @property
    def n_coarray(self) -> int:
        return len(self.coarray)

    def summary_row(self) -> dict:
        """Flat dict for a results table or a CSV row. Given."""
        return {
            "label": self.config.label,
            "formation": self.config.formation,
            "n_uav": self.config.n_uav,
            "n_elements": self.scenario.total_elements,
            "n_snapshots": self.config.n_snapshots,
            "strategy": self.config.strategy,
            "coarray_points": self.n_coarray,
            "coarray_gain": self.coarray_gain,
            **self.metrics.as_dict(),
            "compute_ms": self.compute_ms,
        }


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def build_snapshots(config: SimConfig) -> tuple[list[np.ndarray], list[np.ndarray],
                                                list[np.ndarray]]:
    """
    Build the snapshot sequence and apply every error source.

    Returns (actual, nominal, phase_errors) — the three things `measure` wants.
    `actual` is where the drones really are; `nominal` is where the beamformer
    thinks they are. They differ only when position error is switched on, and
    that difference is the whole reason `coherent_gain` responds to error at all.

    """
    if config.formation == "random":
        base = get_formation(config.formation, config.n_uav, config.aperture, seed=config.seed)
    else:
        base = get_formation(config.formation, config.n_uav, config.aperture)

    rng = np.random.default_rng(config.seed)
    seq = build_sequence(base, config.strategy, config.n_snapshots, config.aperture, rng, config.shift_fraction, config.rotate_total_deg)

    wavelength = config.to_scenario().wavelength
    sigma_pos_metres = config.sigma_pos_lambda * wavelength

    return apply_errors(seq, sigma_pos_metres, config.sigma_phase_rad, config.n_drop, config.seed)



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def run(config: SimConfig, preview: bool = False,
        progress: Callable[[float, str], None] | None = None) -> Result:
    """
    Compute everything for one configuration. THE function the GUI calls.

    Parameters
    ----------
    preview : use a coarse grid for responsiveness while a slider is moving.
    progress : optional callback(fraction, message) so the GUI can show a bar on
        the slow paths. Call it sparingly — a callback per grid row will make the
        run slower than the physics.


    A REAL TRAP: Measure() and point_spread_function() both compute the PSF, so the naive 
    version does the expensive work TWICE. Notice it now rather than wondering later why the
    app feels sluggish. Either compute the image once and derive the metrics from
    it yourself, or accept the cost and note it in a comment — but decide
    deliberately rather than by accident.

    *****
    My solution for the above-mentioned problem is to change the measure() function itself,
    such that it accepts image and axis as parameters rather than it calls point_spread_function().
    I am not doing it right now as I require permission of whether or not I could change it.
    """

    global _CACHE
    global _HITS
    global _MISSES    

    problems = config.validate()
    if problems:
        problem_string = ""
        for idx, problem in enumerate(problems):
            problem_string += f"{idx + 1}. {problem}\n"
        raise ValidationError(problem_string)

    key = (config.cache_key(), preview)
    
    
    
    if key in _CACHE.keys():
        _HITS += 1
        cached = _CACHE[key]
        return replace(cached, from_cache=True)
    else:
        start = perf_counter()
        _MISSES += 1
        if(preview):
            scenario = replace(config.to_scenario(), grid_points=101)
        else:
            scenario = config.to_scenario()

        snapshot_data = build_snapshots(config)
        actual = snapshot_data[0]
        nominal = snapshot_data[1]
        phase_errors = snapshot_data[2]

        if(config.apply_coherence_cost):
            (weights, morph_times) = sequence_weights(actual, config.drone_speed, config.allan_dev, scenario.f0)
        else:
            weights = list(np.ones(config.n_snapshots))
            morph_times = list(np.zeros_like(weights))

        (axis, image) = point_spread_function(actual, scenario, weights, phase_errors)

        metrics = measure(actual, scenario, weights, phase_errors, nominal)
        coarray = fused_coarray(actual)
        gain = coarray_gain(actual)

        end = perf_counter()

        elapsed_time = (end - start)*1000

        result = Result(config, scenario, actual, nominal, weights, morph_times, axis, image, metrics, coarray, gain, elapsed_time, from_cache=False, preview=preview)
        _CACHE.update({key: result})

        return result


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_HITS = 0
_MISSES = 0


def clear_cache() -> None:
    """
    Empty the cache. The GUI wants this on a button.
    """
    global _CACHE
    global _HITS
    global _MISSES

    _CACHE = {}
    _HITS = 0
    _MISSES = 0


def cache_stats() -> dict:
    """
    Hits, misses, entries, hit rate. Put this in the sidebar — watching the hit
    rate while you use the app teaches you more about your own cache key than any
    amount of reasoning.

    """

    hit_rate = 0 if ((_HITS + _MISSES) == 0) else (_HITS/(_HITS + _MISSES))
    entries = len(_CACHE)

    cache_stats = {
        'hits': _HITS,
        'misses': _MISSES,
        'hit_rate': hit_rate,
        'entries': entries
    }

    return cache_stats


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def estimate_cost(config: SimConfig, preview: bool = False) -> float:
    """
    Predict how long `run` will take, in seconds, WITHOUT running it.

    The GUI uses this to decide whether to compute immediately or show a "Compute"
    button — an estimate over ~0.5 s means don't do it on every slider drag.

    """

    k = 2.6936e-07         # I identified this value after comparing the values resulted from 100 test runs on different configs.

    if(preview):
        cost = k * (101 ** 2) * config.n_uav * config.n_snapshots
    else:
        cost = k * (config.grid_points ** 2) * config.n_uav * config.n_snapshots
        
    return cost
    

# ---------------------------------------------------------------------------
# TODO(W11-1) — batch sweeps, week 11
# ---------------------------------------------------------------------------
def sweep(base: SimConfig, parameter: str, values: list,
          progress: Callable[[float, str], None] | None = None) -> list[Result]:
    """
    Run one configuration repeatedly with a single parameter varied.

    This is what turns a toy into an instrument: instead of dragging a slider and
    squinting, the user gets a curve.

    TODO(W11-1): Implement in week 11.
      - for each value: replace() that field on `base`, run it, collect
      - skip invalid combinations rather than crashing (sweeping n_uav across a
        square formation will hit 20, which is not a perfect square — either snap
        with nearest_valid_count or skip and report)
      - report progress; a 20-point sweep takes several seconds
      - the cache makes re-running a sweep with one extra point nearly free,
        which is a nice thing to demonstrate
    """
    raise NotImplementedError("TODO(W11-1) in simulator/engine.py")
