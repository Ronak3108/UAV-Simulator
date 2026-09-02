"""
The cost of changing shape: reconfiguration time and coherence loss.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

Morphing is not free. Drones have to fly somewhere, which takes time and battery,
and while they move their oscillators drift apart. Coherent combining across
snapshots needs phase agreement to a small fraction of a wavelength (1.5 mm at
10 GHz), so a long morph degrades the very fusion it was meant to improve.

    more morphing -> better co-array coverage -> better image
    more morphing -> more drift               -> worse coherence -> worse image

Somewhere in between is the optimum, and letting a user find it by dragging a
slider is one of the best things your simulator can offer.
"""
from __future__ import annotations

import numpy as np

__all__ = ["assignment", "morph_time", "coherence_penalty", "sequence_weights",
           "pareto_front"]


def assignment(formation_a: np.ndarray, formation_b: np.ndarray):
    """
    Cheapest drone-to-slot matching between two formations.

    Returns (total_distance_m, max_distance_m, column_indices).

    The naive "drone i goes to slot i" can cost several times more flying, because
    the two formations may be indexed in completely different orders. This solves
    it exactly with the Hungarian algorithm.
    """
    from scipy.optimize import linear_sum_assignment

    a = np.asarray(formation_a, dtype=float)
    b = np.asarray(formation_b, dtype=float)
    cost = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    rows, cols = linear_sum_assignment(cost)
    d = cost[rows, cols]
    return float(d.sum()), float(d.max()), cols


def morph_time(formation_a, formation_b, speed: float = 5.0) -> float:
    """
    Seconds to reconfigure, assuming all drones move at once at `speed` m/s.

    Set by the drone with FURTHEST to fly, not by total distance — they move in
    parallel. 5 m/s is a conservative figure for a small multirotor with a payload.
    """
    _, longest, _ = assignment(formation_a, formation_b)
    return float(longest / max(speed, 1e-9))


def coherence_penalty(
    elapsed_s: float, allan_dev: float = 1e-11, f0: float = 10e9
) -> float:
    """
    Coherence factor in (0, 1] after `elapsed_s` of oscillator drift.

    Standard result for the mean of exp(j*phi) with zero-mean Gaussian phi:

        phase_variance = (2*pi*f0*allan_dev*elapsed)^2
        factor = exp(-phase_variance / 2)

    allan_dev 1e-11 is a good temperature-compensated crystal; 1e-13 is a
    chip-scale atomic clock (far more expensive and heavier). Offering both in the
    GUI is worthwhile: if the best strategy depends on which oscillator you buy,
    that is a genuinely useful system-design conclusion.

    SIMPLIFICATIONS, which should be stated in any report: this ignores
    vibration-induced phase noise, thermal transients, and the fact that a real
    system would re-synchronise between snapshots over its data link.
    """
    var = (2 * np.pi * f0 * allan_dev * max(elapsed_s, 0.0)) ** 2
    return float(np.exp(-var / 2))


def sequence_weights(
    formations, speed: float = 5.0, allan_dev: float = 1e-11, f0: float = 10e9
) -> tuple[list[float], list[float]]:
    """
    Per-snapshot combining weights after accumulated morph time, plus the
    cumulative time at each snapshot.

    Feed the weights straight into `imaging.point_spread_function(weights=...)`.
    Returns (weights, cumulative_times).
    """
    weights, times, t = [1.0], [0.0], 0.0
    for i in range(1, len(formations)):
        t += morph_time(formations[i - 1], formations[i], speed)
        times.append(t)
        weights.append(coherence_penalty(t, allan_dev, f0))
    return weights, times


def pareto_front(costs: np.ndarray, qualities: np.ndarray) -> np.ndarray:
    """
    Indices of non-dominated points (both axes lower-is-better), sorted by cost.
    O(M^2) and deliberately simple — you will have hundreds of points, not millions.
    """
    c = np.asarray(costs, dtype=float)
    q = np.asarray(qualities, dtype=float)
    keep = [
        i for i in range(len(c))
        if not np.any((c <= c[i]) & (q <= q[i]) & ((c < c[i]) | (q < q[i])))
    ]
    keep = np.array(keep, dtype=int)
    return keep[np.argsort(c[keep])]
