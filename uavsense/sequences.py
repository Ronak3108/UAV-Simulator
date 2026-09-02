"""
Multi-snapshot formation sequences.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

THE IDEA YOUR SIMULATOR EXISTS TO LET PEOPLE EXPLORE
----------------------------------------------------
A snapshot is one complete measurement by the whole formation. Combine K
snapshots coherently and you get the UNION of their co-arrays.

Fly the SAME formation twice and the second snapshot lands on co-array points you
already had: you gain signal-to-noise but ZERO new geometry.

Fly a DIFFERENT one, chosen so its co-array falls into the first one's gaps, and
you fill in the aperture and the ghosts fade.

With the defaults (16 drones, 40 m):

    square + square       ->  49 points, gain 1.00, nothing changes
    square + half-shift   ->  62 points, gain 1.27, ground-range PSLR -22.5 -> -30.0 dB
    square + X            -> 133 points, gain 2.71, cross-range ghost -0.2 -> -6.1 dB

Note the last two fix DIFFERENT defects. No single strategy wins on both, which
is exactly what makes a simulator worth building — there is a real trade-off to
explore rather than one right answer to look up.
"""
from __future__ import annotations

import numpy as np

from .formations import get_formation, translate, rotate

__all__ = ["build_sequence", "SEQUENCE_STRATEGIES", "describe_strategy"]

#: Strategies your GUI offers in its "how should snapshots differ?" dropdown.
SEQUENCE_STRATEGIES = ["repeat", "shift", "rotate", "jitter", "shapes"]


def describe_strategy(kind: str) -> str:
    """One-line help text for the GUI."""
    return {
        "repeat": "Same formation every snapshot — the baseline. Adds SNR, no new geometry.",
        "shift": "Translate by a fraction of the element spacing. Interleaves the co-array.",
        "rotate": "Rotate about the centre. Good against directional sidelobes.",
        "jitter": "Random perturbation each snapshot. Breaks periodicity, less predictable.",
        "shapes": "Cycle through different formation shapes. Largest co-array gain.",
    }.get(kind, "")


def build_sequence(
    base: np.ndarray,
    kind: str,
    n_snapshots: int,
    aperture: float,
    rng: np.random.Generator | None = None,
    shift_fraction: float = 0.5,
    rotate_total_deg: float = 90.0,
    shape_cycle: tuple[str, ...] = ("square", "x", "ring", "diamond"),
) -> list[np.ndarray]:
    """
    Build a list of snapshot formations from one base formation.

    Parameters
    ----------
    kind : one of SEQUENCE_STRATEGIES
    shift_fraction : for "shift", how far to move per snapshot as a fraction of
        the element spacing. 0.5 (half-spacing) interleaves the co-array best; a
        full spacing would put drones where their neighbours were, which is a
        repeat with extra steps.
    rotate_total_deg : for "rotate", total rotation spread across the snapshots.
    shape_cycle : for "shapes", which shapes to cycle through.
    """
    base = np.asarray(base, dtype=float)
    n = len(base)
    if rng is None:
        rng = np.random.default_rng(0)
    if n_snapshots < 1:
        raise ValueError("n_snapshots must be at least 1")

    side = max(int(round(np.sqrt(n))), 2)
    spacing = aperture / (side - 1)
    out: list[np.ndarray] = []

    for k in range(n_snapshots):
        if kind == "repeat":
            out.append(base.copy())
        elif kind == "shift":
            step = spacing * shift_fraction * k / max(n_snapshots - 1, 1)
            out.append(translate(base, np.array([step, step])))
        elif kind == "rotate":
            ang = np.radians(rotate_total_deg) * k / max(n_snapshots, 1)
            out.append(rotate(base, ang))
        elif kind == "jitter":
            if k == 0:
                out.append(base.copy())
            else:
                out.append(base + rng.uniform(-spacing / 2, spacing / 2, base.shape))
        elif kind == "shapes":
            name = shape_cycle[k % len(shape_cycle)]
            try:
                out.append(get_formation(name, n, aperture))
            except ValueError:
                out.append(base.copy())      # count invalid for that shape
        else:
            raise ValueError(f"unknown strategy {kind!r}; options {SEQUENCE_STRATEGIES}")

    return out
