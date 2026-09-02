"""
Realistic imperfections: position error, phase error, dropped drones.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

Pass an rng in rather than creating one inside, so a Monte-Carlo run shares one
reproducible stream and your GUI can offer a "seed" box that actually works.
"""
from __future__ import annotations

import numpy as np

__all__ = ["position_jitter", "phase_noise", "drop_uavs", "apply_errors",
           "degradation_threshold"]


def position_jitter(
    positions: np.ndarray, sigma: float, rng: np.random.Generator
) -> np.ndarray:
    """Independent Gaussian position error, sigma in METRES, on x and y."""
    p = np.asarray(positions, dtype=float)
    if sigma <= 0:
        return p.copy()
    return p + rng.normal(0.0, sigma, size=p.shape)


def phase_noise(n: int, sigma_rad: float, rng: np.random.Generator) -> np.ndarray:
    """Per-drone phase offset in radians from imperfect oscillator sync."""
    if sigma_rad <= 0:
        return np.zeros(n)
    return rng.normal(0.0, sigma_rad, size=n)


def drop_uavs(
    positions: np.ndarray, n_drop: int, rng: np.random.Generator
) -> np.ndarray:
    """Remove n_drop drones at random — battery failure, comms loss, or worse."""
    p = np.asarray(positions, dtype=float)
    if n_drop <= 0:
        return p.copy()
    n_drop = min(n_drop, len(p) - 1)
    keep = np.sort(rng.choice(len(p), size=len(p) - n_drop, replace=False))
    return p[keep]


def apply_errors(
    formations,
    sigma_pos: float = 0.0,
    sigma_phase: float = 0.0,
    n_drop: int = 0,
    seed: int = 0,
):
    """
    Apply every error source to a snapshot sequence in one call.

    Returns (actual_formations, nominal_formations, phase_errors) — exactly the
    three things `imaging.measure` wants. Dropping is applied first so the nominal
    and actual lists stay the same length per snapshot.
    """
    rng = np.random.default_rng(seed)
    actual, nominal, phases = [], [], []
    for P in formations:
        kept = drop_uavs(np.asarray(P, dtype=float), n_drop, rng)
        nominal.append(kept)
        actual.append(position_jitter(kept, sigma_pos, rng))
        phases.append(phase_noise(len(kept), sigma_phase, rng))
    return actual, nominal, phases


def degradation_threshold(
    sigmas: np.ndarray, values: np.ndarray, target: float
) -> float:
    """
    Interpolated x where a decreasing curve first crosses `target`.
    Returns nan if it never crosses. Used for "error level that halves the gain".
    """
    s = np.asarray(sigmas, dtype=float)
    v = np.asarray(values, dtype=float)
    below = np.where(v < target)[0]
    if below.size == 0:
        return float("nan")
    i = int(below[0])
    if i == 0:
        return float(s[0])
    x0, x1, y0, y1 = s[i - 1], s[i], v[i - 1], v[i]
    if y1 == y0:
        return float(x1)
    return float(x0 + (target - y0) / (y1 - y0) * (x1 - x0))
