"""
The per-drone uniform rectangular array (URA).

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

TWO LEVELS OF ARRAY
-------------------
This system is an array of arrays, and the two levels do completely different jobs:

    SWARM LEVEL   16 drones, tens of metres apart (~440 wavelengths)
                  -> sets RESOLUTION and creates GRATING LOBES

    DRONE LEVEL   n_x by n_y elements, half a wavelength apart (~1.5 cm)
                  -> sets each drone's FIELD OF VIEW and its GAIN

The total response is the product of the two:

    total(r) = swarm_factor(r) * drone_factor(r)

WHY THE SUB-ARRAY CAN USE A FAR-FIELD APPROXIMATION
---------------------------------------------------
The swarm spans 40 m and the target is 583 m away, which is close enough to the
near-field boundary that the swarm-level maths must use exact ranges. But one
drone's URA spans only a few centimetres, so for the sub-array the target really
is at infinity. That lets the URA factor depend only on DIRECTION, which is what
makes it almost free to compute.

THE DIRICHLET TRICK
-------------------
A rectangular grid separates into two independent 1-D sums, and each has a closed
form (the Dirichlet kernel):

    sum_{m} exp(j*m*psi)  =  sin(M*psi/2) / sin(psi/2)      (centred array)

So an n_x by n_y URA costs the same as evaluating two sines — no loop over
elements at all. A 16x16 URA is no slower than a 2x2 one. This is why the GUI can
offer a slider up to 32x32 elements without the app becoming unusable.
"""
from __future__ import annotations

import numpy as np

from .config import Scenario, URA

__all__ = [
    "direction_cosines",
    "steering_cosines",
    "dirichlet",
    "ura_factor",
    "ura_pattern_grid",
    "ura_pattern_cut",
]


def dirichlet(psi: np.ndarray, m: int) -> np.ndarray:
    """
    Centred uniform-array factor: sum over m elements of exp(j*m*psi), normalised
    so the peak is 1.0.

        D(psi) = sin(M*psi/2) / (M * sin(psi/2))

    Real-valued (can go negative between lobes). The array is centred on the
    origin, so there is no spurious linear phase term.

    At psi = 0 the expression is 0/0; the limit is 1.0 and is handled here.
    """
    psi = np.asarray(psi, dtype=float)
    if m <= 1:
        return np.ones_like(psi)

    half = psi * 0.5
    denom = np.sin(half)
    small = np.abs(denom) < 1e-12

    # Main branch, computed over the whole array.
    out = np.sin(m * half) / (m * np.where(small, 1.0, denom))

    # Singular points (psi = 2*pi*integer: boresight and grating lobes) need
    # L'Hopital. There are only ever a handful, so patch just those rather than
    # evaluating two more transcendentals over the entire grid — that detail is
    # worth ~40% of the total runtime at a 201x201 grid.
    if small.any():
        h = half[small]
        out[small] = np.cos(m * h) / np.cos(h)
    return out


def direction_cosines(
    drone_xy: np.ndarray, altitude: float, targets: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Direction cosines (u, v) from each drone to each target point.

    The URA lies in the horizontal plane on the underside of the drone, so its
    boresight points straight down (-z) and the relevant direction cosines are the
    x and y components of the unit vector from drone to target.

    Parameters
    ----------
    drone_xy : (N, 2) horizontal drone positions [m]
    altitude : float, drone height [m]
    targets  : (G, 3) target points [m]

    Returns
    -------
    (u, v) each of shape (G, N).
    """
    drone_xy = np.asarray(drone_xy, dtype=float)
    targets = np.asarray(targets, dtype=float)

    # Component-wise rather than np.linalg.norm on a (G, N, 3) stack: that stack
    # is ~250 MB at a 401x401 grid and the allocation dominates the arithmetic.
    dx = targets[:, 0][:, None] - drone_xy[:, 0][None, :]
    dy = targets[:, 1][:, None] - drone_xy[:, 1][None, :]
    dz = targets[:, 2][:, None] - altitude

    r = dx * dx
    r += dy * dy
    r += dz * dz
    np.sqrt(r, out=r)
    np.maximum(r, 1e-12, out=r)
    return dx / r, dy / r


def steering_cosines(
    drone_xy: np.ndarray, altitude: float, focus: np.ndarray, ura: URA
) -> tuple[np.ndarray, np.ndarray]:
    """
    Where each drone's URA is electronically pointed, as direction cosines.

    The base direction is the scene centre (so every drone looks at the target
    area). The URA's steer_az_deg / steer_el_deg then add an offset in
    direction-cosine space, which is the standard convention for a planar array:
    u = sin(theta)*cos(phi), and steering by an angle adds sin(angle).

    Returns (u_s, v_s), each of shape (N,).
    """
    u0, v0 = direction_cosines(drone_xy, altitude, focus[None, :])
    du = np.sin(np.radians(ura.steer_az_deg))
    dv = np.sin(np.radians(ura.steer_el_deg))
    return u0[0] + du, v0[0] + dv


def ura_factor(
    drone_xy: np.ndarray,
    targets: np.ndarray,
    focus: np.ndarray,
    scenario: Scenario,
) -> np.ndarray:
    """
    One-way URA amplitude for every (target, drone) pair. Peak 1.0 at boresight.

    Returns (G, N). If the URA is disabled this is all ones — every drone becomes
    a single isotropic antenna and the whole thing reduces to the single-element
    case, which is a useful A/B to have one checkbox away.

    Multiply this into the swarm sum to get the two-level response.
    """
    ura = scenario.ura
    if not ura.enabled or (ura.n_x <= 1 and ura.n_y <= 1):
        return np.ones((len(targets), len(drone_xy)))

    lam = scenario.wavelength
    d = ura.spacing_wavelengths * lam
    k = scenario.wavenumber

    u, v = direction_cosines(drone_xy, scenario.altitude, targets)      # (G, N)
    u_s, v_s = steering_cosines(drone_xy, scenario.altitude, focus, ura)

    psi_x = k * d * (u - u_s[None, :])
    psi_y = k * d * (v - v_s[None, :])
    return dirichlet(psi_x, ura.n_x) * dirichlet(psi_y, ura.n_y)


def ura_pattern_grid(
    scenario: Scenario, half_angle_deg: float = 60.0, n: int = 401
) -> tuple[np.ndarray, np.ndarray]:
    """
    The URA's own beam pattern over a wide angular window, for display.

    This is the sub-array on its own, ignoring the swarm — the panel that shows
    the student what changing n_x, n_y or element spacing actually does.

    Returns (angles_deg, pattern) where pattern is (n, n), normalised to peak 1,
    indexed [elevation, azimuth].
    """
    ura = scenario.ura
    ang = np.linspace(-half_angle_deg, half_angle_deg, n)
    if not ura.enabled:
        return ang, np.ones((n, n))

    lam = scenario.wavelength
    d = ura.spacing_wavelengths * lam
    k = scenario.wavenumber

    u = np.sin(np.radians(ang))
    U, V = np.meshgrid(u, u)
    u_s = np.sin(np.radians(ura.steer_az_deg))
    v_s = np.sin(np.radians(ura.steer_el_deg))

    pat = np.abs(
        dirichlet(k * d * (U - u_s), ura.n_x)
        * dirichlet(k * d * (V - v_s), ura.n_y)
    )
    return ang, pat / max(pat.max(), 1e-12)


def ura_pattern_cut(
    scenario: Scenario, axis: str = "az", half_angle_deg: float = 60.0, n: int = 1001
) -> tuple[np.ndarray, np.ndarray]:
    """
    A single azimuth or elevation cut through the URA pattern. Returns
    (angles_deg, amplitude) with peak 1.0. Cheap — use this for live GUI updates
    and keep `ura_pattern_grid` for the 2-D display.
    """
    ura = scenario.ura
    ang = np.linspace(-half_angle_deg, half_angle_deg, n)
    if not ura.enabled:
        return ang, np.ones(n)

    lam = scenario.wavelength
    d = ura.spacing_wavelengths * lam
    k = scenario.wavenumber
    u = np.sin(np.radians(ang))

    if axis == "az":
        m, steer = ura.n_x, np.sin(np.radians(ura.steer_az_deg))
    else:
        m, steer = ura.n_y, np.sin(np.radians(ura.steer_el_deg))

    return ang, np.abs(dirichlet(k * d * (u - steer), m))
