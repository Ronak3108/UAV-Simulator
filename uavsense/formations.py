"""
Formation geometry generators.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

A formation is an (N, 2) array of horizontal drone positions in metres, centred
on the origin. Altitude is added by the imaging code, so it does not appear here.

THE FAIRNESS RULE
-----------------
Every generator normalises its output to the SAME bounding aperture. If one shape
spanned 28 m and another 40 m, the second would win on resolution and that would
tell you nothing about shape — only that 40 > 28. Your GUI should expose aperture
as one slider that applies to whichever shape is selected, never per shape.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "normalise_aperture", "square", "ring", "diamond", "cross_x",
    "random_formation", "spiral", "nested", "translate", "rotate",
    "flight_path", "FORMATION_REGISTRY", "get_formation", "list_formations",
]


def normalise_aperture(positions: np.ndarray, aperture: float) -> np.ndarray:
    """Centre on the origin and scale so the widest extent is exactly `aperture`."""
    p = np.asarray(positions, dtype=float)
    p = p - p.mean(axis=0)
    scale = max(np.abs(p[:, 0]).max(), np.abs(p[:, 1]).max())
    if scale < 1e-12:
        return p
    return p * (aperture / 2.0) / scale


def square(n: int, aperture: float) -> np.ndarray:
    """Filled square grid. Needs a perfect square n (4, 9, 16, 25, ...)."""
    side = int(round(np.sqrt(n)))
    if side * side != n:
        raise ValueError(f"square() needs a perfect square count, got {n}")
    g = np.linspace(-aperture / 2, aperture / 2, side)
    gx, gy = np.meshgrid(g, g)
    return np.column_stack([gx.ravel(), gy.ravel()])


def ring(n: int, aperture: float) -> np.ndarray:
    """n drones evenly spaced on a circle of diameter `aperture`."""
    t = np.arange(n) * 2 * np.pi / n
    r = aperture / 2
    return np.column_stack([r * np.cos(t), r * np.sin(t)])


def diamond(n: int, aperture: float) -> np.ndarray:
    """Square grid rotated 45 degrees, renormalised to the same bounding box."""
    return normalise_aperture(rotate(square(n, aperture), np.pi / 4), aperture)


def cross_x(n: int, aperture: float) -> np.ndarray:
    """Two crossed diagonal arms, n/2 drones on each. Needs even n."""
    if n % 2:
        raise ValueError(f"cross_x() needs an even count, got {n}")
    t = np.linspace(-1.0, 1.0, n // 2) * (aperture / 2)
    return np.vstack([np.column_stack([t, t]), np.column_stack([t, -t])])


def random_formation(n: int, aperture: float, seed: int | None = None) -> np.ndarray:
    """Uniform random placement inside the bounding box. The control case."""
    rng = np.random.default_rng(seed)
    return rng.uniform(-aperture / 2, aperture / 2, size=(n, 2))


def spiral(n: int, aperture: float, turns: float = 2.0) -> np.ndarray:
    """
    Archimedean spiral — aperiodic, so no grating lobes, but still structured.
    A good foil for the square in the GUI: same drones, no ghosts.
    """
    t = np.linspace(0.0, 1.0, n)
    theta = 2 * np.pi * turns * t
    r = (aperture / 2) * t
    return normalise_aperture(
        np.column_stack([r * np.cos(theta), r * np.sin(theta)]), aperture
    )


def nested(n: int, aperture: float, inner_fraction: float = 0.4) -> np.ndarray:
    """
    Two concentric rings, half the drones on each. Deliberately non-uniform radius
    so the co-array fills more evenly than a single ring.
    """
    half = n // 2
    outer = ring(half, aperture)
    inner = ring(n - half, aperture * inner_fraction)
    inner = rotate(inner, np.pi / max(n - half, 1))
    return np.vstack([outer, inner])


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------
def translate(positions: np.ndarray, offset: np.ndarray) -> np.ndarray:
    """Shift a whole formation by (dx, dy)."""
    return np.asarray(positions, dtype=float) + np.asarray(offset, dtype=float)


def rotate(positions: np.ndarray, angle_rad: float) -> np.ndarray:
    """Rotate a formation about its centre."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.asarray(positions, dtype=float) @ np.array([[c, -s], [s, c]]).T


def flight_path(
    positions: np.ndarray, velocity: np.ndarray, times: np.ndarray
) -> list[np.ndarray]:
    """Formation position at each time, flying at constant velocity."""
    v = np.asarray(velocity, dtype=float)
    return [np.asarray(positions, dtype=float) + v * float(t) for t in times]


# ---------------------------------------------------------------------------
# Registry — the GUI populates its dropdown from this
# ---------------------------------------------------------------------------
FORMATION_REGISTRY = {
    "square": square,
    "ring": ring,
    "diamond": diamond,
    "x": cross_x,
    "spiral": spiral,
    "nested": nested,
    "random": random_formation,
}

#: Which counts each generator accepts. Your GUI should use this to grey out or
#: snap invalid combinations rather than letting the user trigger a ValueError.
FORMATION_CONSTRAINTS = {
    "square": "perfect square (4, 9, 16, 25, 36, ...)",
    "diamond": "perfect square (4, 9, 16, 25, 36, ...)",
    "x": "even",
    "ring": "any",
    "spiral": "any",
    "nested": "any",
    "random": "any",
}


def list_formations() -> list[str]:
    """Names available to a dropdown, in a sensible display order."""
    return list(FORMATION_REGISTRY)


def get_formation(name: str, n: int, aperture: float, **kwargs) -> np.ndarray:
    """Look up a generator by name and call it."""
    try:
        fn = FORMATION_REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown formation {name!r}; options are {sorted(FORMATION_REGISTRY)}"
        ) from None
    return fn(n, aperture, **kwargs)


def valid_count(name: str, n: int) -> bool:
    """True if `n` drones is a legal count for this formation."""
    if name in ("square", "diamond"):
        s = int(round(np.sqrt(n)))
        return s * s == n
    if name == "x":
        return n % 2 == 0
    return n >= 1


def nearest_valid_count(name: str, n: int) -> int:
    """Closest legal drone count to `n` — use this to snap a GUI slider."""
    if valid_count(name, n):
        return n
    if name in ("square", "diamond"):
        s = max(int(round(np.sqrt(n))), 2)
        return s * s
    if name == "x":
        return max(n - (n % 2), 2)
    return max(n, 1)
