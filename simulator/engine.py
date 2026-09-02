"""
The compute layer — turns a SimConfig into a Result, and does it fast enough.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
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
doubles every number above — which is the trap flagged in TODO(W03-3).

Build `run(config, preview=True/False)` around that from the start; retrofitting
it later means touching every call site.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from uavsense.config import Scenario
from uavsense.imaging import PSFMetrics

from .state import SimConfig

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
# TODO(W03-2)
# ---------------------------------------------------------------------------
def build_snapshots(config: SimConfig) -> tuple[list[np.ndarray], list[np.ndarray],
                                                list[np.ndarray]]:
    """
    Build the snapshot sequence and apply every error source.

    Returns (actual, nominal, phase_errors) — the three things `measure` wants.
    `actual` is where the drones really are; `nominal` is where the beamformer
    thinks they are. They differ only when position error is switched on, and
    that difference is the whole reason `coherent_gain` responds to error at all.

    TODO(W03-2): Implement this.
      1. base = uavsense.formations.get_formation(config.formation, n_uav, aperture)
         (pass seed=config.seed when the formation is "random")
      2. seq = uavsense.sequences.build_sequence(base, config.strategy,
                  config.n_snapshots, config.aperture, rng, config.shift_fraction,
                  config.rotate_total_deg)
      3. uavsense.errors.apply_errors(seq, sigma_pos, sigma_phase, n_drop, seed)
         — note sigma_pos_lambda is in WAVELENGTHS and apply_errors wants METRES,
         so multiply by the wavelength. Getting this wrong by a factor of 30 is
         an easy mistake and the symptom (nothing seems to degrade) looks like a
         physics problem rather than a units problem.

    Keep this separate from `run` so you can unit-test the sequence logic without
    computing a single PSF.
    """
    raise NotImplementedError("TODO(W03-2) in simulator/engine.py")


# ---------------------------------------------------------------------------
# TODO(W03-3)
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

    TODO(W03-3): Implement this.
      1. cfg validation: if config.validate() is non-empty, raise ValidationError.
         Fail here, not deep inside numpy where the message is unreadable.
      2. check the cache (see TODO(W03-4)); return the hit with from_cache=True
      3. scenario = config.to_scenario(); if preview, replace() its grid_points
         with something coarse (101 is a good default)
      4. actual, nominal, phases = build_snapshots(config)
      5. weights: all 1.0, unless config.apply_coherence_cost, in which case use
         uavsense.costs.sequence_weights(...)
      6. axis, image = point_spread_function(actual, scenario, weights, phases)
      7. metrics = measure(actual, scenario, weights, phases, nominal=nominal)
         — passing `nominal` is what makes peak_gain meaningful
      8. coarray = uavsense.coarray.fused_coarray(actual)
      9. time it with time.perf_counter, store compute_ms, cache it, return

    A REAL TRAP: steps 6 and 7 both compute the PSF, so the naive version does
    the expensive work TWICE. Notice it now rather than wondering later why the
    app feels sluggish. Either compute the image once and derive the metrics from
    it yourself, or accept the cost and note it in a comment — but decide
    deliberately rather than by accident.
    """
    raise NotImplementedError("TODO(W03-3) in simulator/engine.py")


# ---------------------------------------------------------------------------
# TODO(W03-4)
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_HITS = 0
_MISSES = 0


def clear_cache() -> None:
    """
    Empty the cache. The GUI wants this on a button.

    TODO(W03-4a): Implement. Reset the hit/miss counters too.
    """
    raise NotImplementedError("TODO(W03-4a) in simulator/engine.py")


def cache_stats() -> dict:
    """
    Hits, misses, entries, hit rate. Put this in the sidebar — watching the hit
    rate while you use the app teaches you more about your own cache key than any
    amount of reasoning.

    TODO(W03-4b): Implement.

    Then go and look at it: if the hit rate stays near zero while you drag a
    slider back and forth over values you have already visited, something in your
    key is changing when it should not. (The classic culprit is a float that
    accumulates rounding, or the label sneaking in.)
    """
    raise NotImplementedError("TODO(W03-4b) in simulator/engine.py")


# ---------------------------------------------------------------------------
# TODO(W03-5)
# ---------------------------------------------------------------------------
def estimate_cost(config: SimConfig, preview: bool = False) -> float:
    """
    Predict how long `run` will take, in seconds, WITHOUT running it.

    The GUI uses this to decide whether to compute immediately or show a "Compute"
    button — an estimate over ~0.5 s means don't do it on every slider drag.

    TODO(W03-5): Implement. Cost is dominated by the range computation, which is
    grid_points^2 * n_uav * n_snapshots. The URA is nearly free thanks to the
    Dirichlet trick, so element count barely enters.

      1. Time one small reference run once, and cache the constant.
      2. Scale it: cost = k * grid_points^2 * n_uav * n_snapshots
      3. Sanity-check the prediction against reality for a few configurations and
         write down how close it gets. A cost model you have not checked is a
         guess with a decimal point on it.
    """
    raise NotImplementedError("TODO(W03-5) in simulator/engine.py")


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
