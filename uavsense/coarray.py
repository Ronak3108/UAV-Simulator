"""
The MIMO sum co-array — the virtual array a formation actually behaves like.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

If drone m transmits and drone n receives, the two-way path length depends on
their MIDPOINT. So N drones create up to N^2 transmit-receive pairs behaving like
a virtual array at all those midpoints. That set is the sum co-array, and

    IMAGE QUALITY IS DETERMINED BY THE CO-ARRAY, NOT BY THE DRONE POSITIONS.

Two formations that look completely different on screen can share a co-array and
produce identical images. This is worth a panel in your GUI: showing the drones
beside their co-array is the single clearest way to explain what the swarm is
doing.

Computing the co-array is ~1000x cheaper than a full PSF, so co-array panels can
update on every slider drag while the PSF panel waits for the user to stop moving.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "sum_coarray", "unique_coarray", "coarray_extent", "fill_fraction",
    "hole_fraction", "redundancy", "fused_coarray", "coarray_gain",
    "complementarity", "occupancy_mask",
]


def sum_coarray(positions: np.ndarray) -> np.ndarray:
    """All N^2 virtual element positions (p_m + p_n)/2, duplicates KEPT."""
    p = np.asarray(positions, dtype=float)
    return ((p[:, None, :] + p[None, :, :]) / 2.0).reshape(-1, 2)


def _snap_unique(points: np.ndarray, tol: float) -> np.ndarray:
    return np.unique(np.round(np.asarray(points) / tol) * tol, axis=0)


def unique_coarray(positions: np.ndarray, tol: float = 0.05) -> np.ndarray:
    """Distinct virtual positions, snapped to a `tol` grid to defeat float noise."""
    return _snap_unique(sum_coarray(positions), tol)


def coarray_extent(positions: np.ndarray) -> tuple[float, float]:
    """
    Co-array width in x and y [m]. Note this equals the formation aperture, not
    double it: the midpoint of the two most distant drones is the centre.
    """
    v = sum_coarray(positions)
    return (
        float(v[:, 0].max() - v[:, 0].min()),
        float(v[:, 1].max() - v[:, 1].min()),
    )


def occupancy_mask(points: np.ndarray, cell: float, aperture: float) -> np.ndarray:
    """Boolean grid marking which aperture cells hold at least one point."""
    n = max(int(np.ceil(aperture / cell)), 1)
    idx = np.floor((np.asarray(points) + aperture / 2) / cell).astype(int)
    idx = np.clip(idx, 0, n - 1)
    mask = np.zeros((n, n), dtype=bool)
    mask[idx[:, 0], idx[:, 1]] = True
    return mask


def fill_fraction(positions: np.ndarray, cell: float, aperture: float) -> float:
    """Fraction of aperture cells containing a virtual element. Higher is better."""
    mask = occupancy_mask(sum_coarray(positions), cell, aperture)
    return float(mask.sum() / mask.size)


def hole_fraction(positions: np.ndarray, cell: float, aperture: float) -> float:
    """1 - fill_fraction. The natural thing to minimise."""
    return 1.0 - fill_fraction(positions, cell, aperture)


def redundancy(positions: np.ndarray, tol: float = 0.05) -> float:
    """
    N^2 / (unique co-array points). 1.0 means every pair measures something new.

    Expect ~5.2 for a 4x4 square (very redundant, because a lattice folds many
    pairs onto the same midpoint) and ~2.0 for a ring.
    """
    n = len(positions)
    return float(n * n / len(unique_coarray(positions, tol)))


# ---------------------------------------------------------------------------
# Multi-snapshot
# ---------------------------------------------------------------------------
def fused_coarray(formations, tol: float = 0.05) -> np.ndarray:
    """Union of the co-arrays of every snapshot, de-duplicated."""
    return _snap_unique(np.vstack([sum_coarray(p) for p in formations]), tol)


def coarray_gain(formations, tol: float = 0.05) -> float:
    """
    Unique fused points divided by unique points in snapshot 0.

    A value of exactly 1.0 means the extra snapshots added NO new geometry — which
    is what you get from repeating one formation. That null result is the thing
    the whole project is built on, so make it visible in the GUI.
    """
    first = len(fused_coarray([formations[0]], tol))
    return float(len(fused_coarray(formations, tol)) / max(first, 1))


def complementarity(
    formation_a: np.ndarray, formation_b: np.ndarray, cell: float, aperture: float
) -> float:
    """
    Fraction of A's EMPTY co-array cells that B fills. 0 = B adds nothing,
    1 = B perfectly completes A.
    """
    ma = occupancy_mask(sum_coarray(formation_a), cell, aperture)
    mb = occupancy_mask(sum_coarray(formation_b), cell, aperture)
    holes = ~ma
    if holes.sum() == 0:
        return 0.0
    return float((mb & holes).sum() / holes.sum())
