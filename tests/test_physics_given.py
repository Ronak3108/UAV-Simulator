"""
The physics library, verified. THESE PASS ON DAY ONE — you did not break anything.

Run this first:  pytest tests/test_physics_given.py -q

Two reasons this file exists:

  1. It proves `uavsense` works, so when your simulator misbehaves you know the
     bug is in YOUR layer. That halves your debugging surface, which is worth a
     great deal in week 9 at midnight.

  2. It documents the numbers your GUI should produce. When a user reports "the
     square shows a ghost", you can point here and say yes, at -0.2 dB, exactly
     as predicted by lambda*R/d = 1.31 m.
"""
import numpy as np
import pytest
from dataclasses import replace

from uavsense import BASE, URA, get_formation, measure, unique_coarray
from uavsense.imaging import point_spread_function, coherent_gain
from uavsense.coarray import fused_coarray, coarray_gain
from uavsense.errors import position_jitter
from uavsense.ura import dirichlet, ura_pattern_cut
from uavsense.sequences import build_sequence

pytestmark = pytest.mark.given

NO_URA = replace(BASE, ura=URA(enabled=False))


# --------------------------------------------------------------------------
# Formation geometry
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["square", "ring", "diamond", "x", "spiral", "nested"])
def test_every_formation_spans_the_same_aperture(name):
    """The fairness rule: shapes are only comparable at equal aperture."""
    p = get_formation(name, 16, 40.0)
    assert p.shape == (16, 2)
    extent = max(abs(p[:, 0]).max(), abs(p[:, 1]).max()) * 2
    assert extent == pytest.approx(40.0, rel=1e-6)


@pytest.mark.parametrize(
    "name,expected", [("square", 49), ("ring", 129), ("diamond", 49), ("x", 93)]
)
def test_coarray_counts(name, expected):
    """Exact. Square and diamond match because a diamond IS a rotated square."""
    assert len(unique_coarray(get_formation(name, 16, 40.0))) == expected


# --------------------------------------------------------------------------
# The URA
# --------------------------------------------------------------------------
@pytest.mark.parametrize("m", [1, 2, 4, 8, 16])
def test_dirichlet_equals_explicit_element_sum(m):
    """The closed form must equal summing over elements one at a time."""
    psi = np.linspace(-3, 3, 97)
    idx = np.arange(m) - (m - 1) / 2
    brute = np.abs(np.exp(1j * np.outer(psi, idx)).sum(axis=1)) / m
    np.testing.assert_allclose(np.abs(dirichlet(psi, m)), brute, atol=1e-10)


@pytest.mark.parametrize("n,expected_deg", [(4, 25.4), (8, 12.7), (16, 6.35)])
def test_ura_beamwidth_matches_theory(n, expected_deg):
    sc = replace(BASE, ura=URA(n_x=n, n_y=n))
    ang, pat = ura_pattern_cut(sc, half_angle_deg=90, n=20001)
    above = ang[pat >= 1 / np.sqrt(2)]
    assert (above.max() - above.min()) == pytest.approx(expected_deg, rel=0.06)


def test_ura_grows_grating_lobes_above_half_wavelength_spacing():
    """
    Two levels of array, two independent ways to make a ghost. At 1.5 lambda
    spacing the URA itself has a full-height lobe near 42 degrees.
    """
    assert URA(spacing_wavelengths=0.5).grating_lobe_angle_deg() is None
    assert URA(spacing_wavelengths=1.5).grating_lobe_angle_deg() == pytest.approx(41.8, abs=0.5)

    sc = replace(BASE, ura=URA(n_x=8, n_y=8, spacing_wavelengths=1.5))
    ang, pat = ura_pattern_cut(sc, half_angle_deg=89, n=20001)
    off = np.abs(ang) > 20
    assert pat[off].max() > 0.99


def test_disabling_the_ura_gives_single_isotropic_elements():
    sc = replace(BASE, ura=URA(enabled=False))
    assert sc.total_elements == sc.n_uav
    ang, pat = ura_pattern_cut(sc)
    np.testing.assert_allclose(pat, 1.0)


def test_ura_multiplies_gain_but_not_resolution():
    """
    The point users get wrong, so it is pinned here: more elements per drone buy
    GAIN, not resolution. Resolution is the swarm's job.
    """
    P = get_formation("ring", 16, 40.0)
    small = replace(BASE, ura=URA(n_x=2, n_y=2))
    big = replace(BASE, ura=URA(n_x=16, n_y=16))

    assert big.array_gain_db - small.array_gain_db == pytest.approx(
        20 * np.log10(256 / 4), abs=0.01
    )
    m_small, m_big = measure([P], small), measure([P], big)
    assert m_big.res_y == pytest.approx(m_small.res_y, rel=0.02)


# --------------------------------------------------------------------------
# Imaging
# --------------------------------------------------------------------------
def test_psf_peak_is_at_the_scene_centre_and_normalised():
    axis, img = point_spread_function([get_formation("ring", 16, 40.0)], BASE)
    assert img.max() == pytest.approx(1.0)
    c = BASE.grid_points // 2
    assert np.unravel_index(img.argmax(), img.shape) == (c, c)


BENCH = {
    "square":  (0.811, 0.215, -22.5, -0.2),
    "ring":    (0.854, 0.227, -15.8, -12.4),
    "diamond": (1.160, 0.308, None, -2.0),
    "x":       (0.924, 0.246, -24.9, -25.7),
}


@pytest.mark.parametrize("name", list(BENCH))
def test_benchmark_numbers(name):
    """The reference table, single element per drone."""
    rx, ry, px, py = BENCH[name]
    m = measure([get_formation(name, 16, 40.0)], NO_URA)
    assert m.res_x == pytest.approx(rx, rel=0.02)
    assert m.res_y == pytest.approx(ry, rel=0.02)
    assert m.pslr_y == pytest.approx(py, abs=1.0)
    if px is None:
        assert np.isnan(m.pslr_x) or m.pslr_x < -35
    else:
        assert m.pslr_x == pytest.approx(px, abs=1.0)


def test_lattices_make_ghosts_and_aperiodic_shapes_do_not():
    """Periodicity, not shape, is what creates a ghost."""
    for lattice in ["square", "diamond"]:
        assert measure([get_formation(lattice, 16, 40.0)], NO_URA).pslr_y > -8.0
    for aperiodic in ["ring", "x", "spiral"]:
        assert measure([get_formation(aperiodic, 16, 40.0)], NO_URA).pslr_y < -10.0


def test_ghost_sits_where_lambda_R_over_d_predicts():
    axis, img = point_spread_function([get_formation("square", 16, 40.0)], NO_URA)
    c = NO_URA.grid_points // 2
    predicted = NO_URA.wavelength * NO_URA.slant_range / (40.0 / 3)
    assert predicted == pytest.approx(1.31, abs=0.05)
    near = np.abs(np.abs(axis) - predicted) < 0.15
    assert img[:, c][near].max() > 0.7


# --------------------------------------------------------------------------
# Multi-snapshot — the project's central claim
# --------------------------------------------------------------------------
def test_repeating_a_formation_adds_no_geometry():
    p = get_formation("square", 16, 40.0)
    assert len(fused_coarray([p, p, p, p])) == 49
    assert coarray_gain([p, p]) == pytest.approx(1.0)


def test_different_shapes_add_a_lot():
    sq, xf = get_formation("square", 16, 40.0), get_formation("x", 16, 40.0)
    assert len(fused_coarray([sq, xf])) == 133
    assert coarray_gain([sq, xf]) == pytest.approx(133 / 49, rel=0.01)


def test_shift_strategy_improves_ground_range_sidelobes():
    sq = get_formation("square", 16, 40.0)
    seq = build_sequence(sq, "shift", 2, 40.0)
    assert measure(seq, NO_URA).pslr_x < measure([sq], NO_URA).pslr_x - 5.0


# --------------------------------------------------------------------------
# Errors — the trap your GUI must not fall into
# --------------------------------------------------------------------------
def test_coherent_gain_collapses_but_pslr_barely_moves():
    """
    THE most important behaviour for your Week 6 panel. Ten wavelengths of
    position error leaves PSLR almost untouched while coherent gain is already at
    the incoherent floor. Show BOTH, or the app will mislead its user.
    """
    p = get_formation("ring", 16, 40.0)
    q = position_jitter(p, 10.0 * BASE.wavelength, np.random.default_rng(7))

    assert abs(measure([q], NO_URA).pslr_x - measure([p], NO_URA).pslr_x) < 3.0
    assert coherent_gain([q], nominal=[p], scenario=NO_URA) < 0.2


def test_coherent_gain_curve():
    """0.1 lambda is 3 mm and already costs a quarter of the gain."""
    p = get_formation("ring", 16, 40.0)
    lam = BASE.wavelength
    gains = [
        np.mean([
            coherent_gain([position_jitter(p, s * lam, np.random.default_rng(t))],
                          nominal=[p], scenario=NO_URA)
            for t in range(40)
        ])
        for s in [0.0, 0.1, 0.25]
    ]
    assert gains[0] == pytest.approx(1.0)
    assert gains[1] == pytest.approx(0.76, abs=0.10)
    assert gains[2] == pytest.approx(0.21, abs=0.10)


# --------------------------------------------------------------------------
# Performance — your GUI depends on these holding
# --------------------------------------------------------------------------
def test_default_grid_is_fast_enough_to_be_interactive():
    import time
    P = get_formation("square", 16, 40.0)
    t0 = time.perf_counter()
    point_spread_function([P], BASE)
    assert time.perf_counter() - t0 < 2.0


def test_cost_scales_as_grid_points_squared():
    """
    The scaling law your preview mode and cost estimate are built on. Absolute
    speed varies wildly by machine; this ratio does not.
    """
    import time
    P = get_formation("square", 16, 40.0)

    def timeit(ng):
        sc = replace(BASE, grid_points=ng)
        point_spread_function([P], sc)              # warm up
        t0 = time.perf_counter()
        point_spread_function([P], sc)
        return time.perf_counter() - t0

    t101, t401 = timeit(101), timeit(401)
    assert t401 > t101 * 4, "quadrupling the grid side should cost far more"


def test_metrics_barely_depend_on_grid_density():
    """
    The fact that makes a coarse preview honest rather than an approximation you
    apologise for: from 101 to 401 points the numbers agree to about 1%. The
    extra samples only smooth the picture.
    """
    P = get_formation("ring", 16, 40.0)
    coarse = measure([P], replace(BASE, ura=URA(enabled=False), grid_points=101))
    fine = measure([P], replace(BASE, ura=URA(enabled=False), grid_points=401))
    assert coarse.res_x == pytest.approx(fine.res_x, rel=0.02)
    assert coarse.res_y == pytest.approx(fine.res_y, rel=0.02)
    assert coarse.pslr_y == pytest.approx(fine.pslr_y, abs=0.5)


def test_large_ura_costs_almost_nothing():
    """The Dirichlet trick: a 32x32 URA must not be slower than a 2x2 one."""
    import time
    P = get_formation("square", 16, 40.0)

    def timeit(n):
        sc = replace(BASE, ura=URA(n_x=n, n_y=n), grid_points=201)
        t0 = time.perf_counter()
        point_spread_function([P], sc)
        return time.perf_counter() - t0

    timeit(2)
    assert timeit(32) < timeit(2) * 2.0
