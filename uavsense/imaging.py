"""
The imaging engine: point spread function, quality metrics, coherent gain.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.

WHAT YOUR SIMULATOR CALLS
-------------------------
    point_spread_function(formations, scenario)  -> (axis, image)
    measure(formations, scenario)                -> PSFMetrics
    coherent_gain(actual, nominal, scenario)     -> float in (0, 1]

Everything else here supports those three.

THE MODEL
---------
For one snapshot, drone positions p_n, target r, focus point r0:

    h(r) = [ sum_n  A_n(r) * exp(-jk( |p_n - r| - |p_n - r0| )) ] ** 2

  - the SQUARE is the MIMO two-way response: every drone transmits and every
    drone receives, so the pairs land on midpoints (the "sum co-array")
  - A_n(r) is drone n's URA amplitude toward r (see uavsense.ura)
  - ranges are EXACT, not a plane-wave approximation: at 583 m with a 40 m
    aperture you are near the near-field boundary and a linearised phase would be
    plausible-looking and wrong

Multiple snapshots are combined coherently with per-snapshot weights w_k, which
is how the multi-snapshot and coherence-loss studies work.

PERFORMANCE, because your GUI depends on it
-------------------------------------------
Cost is dominated by the ranges: O(grid_points^2 * n_uav * n_snapshots). The URA
adds almost nothing thanks to the Dirichlet trick, so element count barely
enters — a 32x32 URA costs about the same as a 2x2 one.

The number that matters is the SQUARE on grid_points. Doubling the grid costs 4x.
Measured on a modest cloud container, one snapshot with 16 drones:

    101 x 101     ~20 ms      genuinely interactive
    201 x 201     ~65 ms      the default; comfortable
    301 x 301    ~155 ms
    401 x 401    ~295 ms      export quality

Your machine will differ, possibly by a lot — measure it rather than trusting
these. What will NOT differ is the scaling law, and that is what your preview
mode and cost estimate should be built on.

And note `measure()` calls this function again, so a naive engine computes the
PSF twice and pays double. That is a deliberate trap left for you to find in
Week 3.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence

import numpy as np

from .config import BASE, Scenario
from .ura import ura_factor

__all__ = [
    "PSFMetrics", "point_spread_function", "resolution_3db", "pslr", "islr",
    "coherent_gain", "measure", "linear_array_pattern",
]


@dataclass
class PSFMetrics:
    """Everything that describes one point spread function."""

    res_x: float        # 3 dB main-lobe width, ground range [m]
    res_y: float        # 3 dB main-lobe width, cross range [m]
    pslr_x: float       # peak sidelobe ratio along x [dB]; nan if none in window
    pslr_y: float       # peak sidelobe ratio along y [dB]
    islr: float         # integrated sidelobe ratio [dB]; CAN be positive
    peak_gain: float    # coherent gain at focus, 1.0 = perfect, ~1/N = lost

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"res = ({self.res_x:.3f}, {self.res_y:.3f}) m   "
            f"PSLR = ({self.pslr_x:.1f}, {self.pslr_y:.1f}) dB   "
            f"ISLR = {self.islr:.1f} dB   gain = {self.peak_gain:.3f}"
        )


# ---------------------------------------------------------------------------
# The core computation
# ---------------------------------------------------------------------------
def _grid(scenario: Scenario) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Imaging grid: returns (axis, target_points, focus_point)."""
    ng = scenario.grid_points
    xs = np.linspace(-scenario.grid_half_width, scenario.grid_half_width, ng)
    gx, gy = np.meshgrid(xs, xs)
    targets = np.stack(
        [gx.ravel() + scenario.ground_range, gy.ravel(), np.zeros(gx.size)], axis=1
    )
    focus = np.array([scenario.ground_range, 0.0, 0.0])
    return xs, targets, focus


def point_spread_function(
    formations: Sequence[np.ndarray],
    scenario: Scenario = BASE,
    weights: Sequence[float] | None = None,
    phase_errors: Sequence[np.ndarray] | None = None,
    return_complex: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Coherent two-level MIMO point spread function over a patch of ground.

    Parameters
    ----------
    formations : sequence of (N, 2) arrays, one per snapshot. Pass a
        single-element list for a static formation.
    weights : per-snapshot combining weight w_k. Defaults to all ones. Use this
        to apply a coherence penalty to later snapshots.
    phase_errors : sequence of (N,) arrays, per-drone phase offsets in radians.
    return_complex : if True, return the complex field instead of normalised
        magnitude (useful if you want to sum images yourself).

    Returns
    -------
    axis  : (G,) ground coordinates [m]
    image : (G, G) normalised magnitude, peak 1.0. Row index is y, column is x.
    """
    xs, targets, focus = _grid(scenario)
    ng = scenario.grid_points
    k = scenario.wavenumber

    if weights is None:
        weights = [1.0] * len(formations)

    acc = np.zeros(targets.shape[0], dtype=complex)

    for i, P in enumerate(formations):
        P = np.asarray(P, dtype=float)
        pos = np.column_stack(
            [P[:, 0], P[:, 1], np.full(len(P), scenario.altitude)]
        )
        # Component-wise distances. np.linalg.norm on a (G, N, 3) stack would
        # allocate ~250 MB at a 401x401 grid; this keeps it to (G, N).
        dx = targets[:, 0][:, None] - pos[:, 0][None, :]
        dy = targets[:, 1][:, None] - pos[:, 1][None, :]
        dz = targets[:, 2][:, None] - pos[:, 2][None, :]
        d_target = dx * dx
        d_target += dy * dy
        d_target += dz * dz
        np.sqrt(d_target, out=d_target)
        d_focus = np.linalg.norm(focus[None, :] - pos, axis=1)

        phase = k * (d_target - d_focus[None, :])
        if phase_errors is not None:
            phase = phase + np.asarray(phase_errors[i])[None, :]

        amp = ura_factor(P, targets, focus, scenario)      # (G, N)
        acc += weights[i] * (np.sum(amp * np.exp(-1j * phase), axis=1)) ** 2

    field = acc.reshape(ng, ng)
    if return_complex:
        return xs, field
    img = np.abs(field)
    peak = img.max()
    return xs, img / (peak if peak > 0 else 1.0)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _interp_crossing(axis, cut, i, j, level):
    if cut[j] == cut[i]:
        return axis[j]
    f = (level - cut[i]) / (cut[j] - cut[i])
    return axis[i] + f * (axis[j] - axis[i])


def resolution_3db(axis: np.ndarray, cut: np.ndarray) -> float:
    """
    Main-lobe width at the -3 dB level, with linear interpolation between samples.

    Note the image holds AMPLITUDE, so -3 dB is 1/sqrt(2), not 1/2.
    """
    axis = np.asarray(axis, dtype=float)
    cut = np.asarray(cut, dtype=float)
    level = 1.0 / np.sqrt(2.0)
    pk = int(np.argmax(cut))

    lo = pk
    while lo > 0 and cut[lo] > level:
        lo -= 1
    hi = pk
    while hi < len(cut) - 1 and cut[hi] > level:
        hi += 1

    left = _interp_crossing(axis, cut, lo, min(lo + 1, len(cut) - 1), level)
    right = _interp_crossing(axis, cut, hi, max(hi - 1, 0), level)
    return float(abs(right - left))


def pslr(axis: np.ndarray, cut: np.ndarray) -> float:
    """
    Peak sidelobe ratio in dB: tallest peak outside the main lobe, relative to the
    main peak.

    Returns nan when the main lobe fills the analysis window and there is no
    sidelobe to measure. That is a real situation, not an error — widen
    `grid_half_width` if you need a number.

    A formation with a full-strength grating lobe returns about 0 dB. That is
    CORRECT: the ghost really is as bright as the target.
    """
    cut = np.asarray(cut, dtype=float)
    pk = int(np.argmax(cut))

    lo = pk
    while lo > 0 and cut[lo - 1] < cut[lo]:
        lo -= 1
    hi = pk
    while hi < len(cut) - 1 and cut[hi + 1] < cut[hi]:
        hi += 1

    side = np.concatenate([cut[: max(lo - 1, 0)], cut[min(hi + 2, len(cut)):]])
    if side.size == 0 or cut[pk] <= 0:
        return float("nan")
    return float(20 * np.log10(max(side.max(), 1e-12) / cut[pk]))


def islr(axis: np.ndarray, image: np.ndarray, mainlobe_radius: float) -> float:
    """
    Integrated sidelobe ratio in dB: energy outside the main lobe over energy
    inside it. Works in POWER, hence 10*log10 (PSLR is amplitude, hence 20).

    CAN BE POSITIVE, and that is not a bug: a formation with a full-strength
    grating lobe genuinely has more energy outside the main lobe than inside.
    """
    axis = np.asarray(axis, dtype=float)
    power = np.asarray(image, dtype=float) ** 2
    gx, gy = np.meshgrid(axis, axis)
    rr = np.hypot(gx, gy)
    inside = power[rr <= mainlobe_radius].sum()
    outside = power[rr > mainlobe_radius].sum()
    if inside <= 0:
        return float("nan")
    return float(10 * np.log10(max(outside, 1e-30) / inside))


def coherent_gain(
    formations: Sequence[np.ndarray],
    nominal: Sequence[np.ndarray] | None = None,
    scenario: Scenario = BASE,
    phase_errors: Sequence[np.ndarray] | None = None,
) -> float:
    """
    How much of the ideal coherent sum survives at the focus. 1.0 = perfect.

    WHY THIS EXISTS, and why your GUI should show it
    ------------------------------------------------
    `point_spread_function` divides by its own peak, so the image is normalised
    no matter how badly the drones are misplaced. That makes PSLR nearly BLIND to
    position error: scramble the drones by ten wavelengths and PSLR barely moves.

    What actually collapses is the coherent sum at the focus — the beamformer
    applies phase weights computed for where the drones were SUPPOSED to be, and
    if they are elsewhere those contributions stop adding in phase.

    Expect ~0.76 at sigma = 0.1 lambda and ~0.21 at 0.25 lambda. lambda is 3 cm,
    so 0.1 lambda is THREE MILLIMETRES. Plain GPS gives metres. That comparison
    is the headline system-design finding of the whole project, so put this
    number somewhere prominent in your GUI.

    A value near 1/N means all phase relationship is lost: you have N independent
    receivers rather than one array.
    """
    if nominal is None:
        nominal = formations
    k = scenario.wavenumber
    focus = np.array([scenario.ground_range, 0.0, 0.0])

    total = 0.0
    for i, P in enumerate(formations):
        P = np.asarray(P, dtype=float)
        Q = np.asarray(nominal[i], dtype=float)
        pa = np.column_stack([P[:, 0], P[:, 1], np.full(len(P), scenario.altitude)])
        pn = np.column_stack([Q[:, 0], Q[:, 1], np.full(len(Q), scenario.altitude)])
        phase = k * (
            np.linalg.norm(focus - pa, axis=1) - np.linalg.norm(focus - pn, axis=1)
        )
        if phase_errors is not None:
            phase = phase + np.asarray(phase_errors[i])
        total += abs(np.exp(-1j * phase).sum()) ** 2 / len(P) ** 2

    return float(total / len(formations))


def measure(
    formations: Sequence[np.ndarray],
    scenario: Scenario = BASE,
    weights: Sequence[float] | None = None,
    phase_errors: Sequence[np.ndarray] | None = None,
    nominal: Sequence[np.ndarray] | None = None,
) -> PSFMetrics:
    """
    Compute the PSF and return all six quality numbers. This is the one call your
    engine layer makes for a single configuration.
    """
    axis, img = point_spread_function(
        formations, scenario, weights=weights, phase_errors=phase_errors
    )
    c = scenario.grid_points // 2
    cut_x, cut_y = img[c, :], img[:, c]
    rx = resolution_3db(axis, cut_x)
    ry = resolution_3db(axis, cut_y)
    return PSFMetrics(
        res_x=rx,
        res_y=ry,
        pslr_x=pslr(axis, cut_x),
        pslr_y=pslr(axis, cut_y),
        islr=islr(axis, img, max(rx, ry) / 2),
        peak_gain=coherent_gain(
            formations, nominal=nominal, scenario=scenario, phase_errors=phase_errors
        ),
    )


def linear_array_pattern(
    n: int, spacing: float, wavelength: float, angles_rad: np.ndarray
) -> np.ndarray:
    """
    Beam pattern of a 1-D uniform linear array, normalised to peak 1.

    Not used by the simulator — kept because it is the simplest possible demo of
    grating lobes, and `scripts/demo_physics.py` uses it to show what happens when
    element spacing exceeds lambda/2.
    """
    k = 2 * np.pi / wavelength
    x = np.arange(n) * spacing
    ph = k * x[None, :] * np.sin(np.asarray(angles_rad, dtype=float))[:, None]
    return np.abs(np.exp(1j * ph).sum(axis=1)) / n
