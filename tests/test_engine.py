"""
Week 3 — the engine. The spec for simulator/engine.py.

Run:  pytest -m week03 -v
"""
import time
import numpy as np
import pytest

from simulator.state import SimConfig, DEFAULT, ValidationError
from simulator import engine

pytestmark = pytest.mark.week03

FAST = DEFAULT.with_(grid_points=101)      # keep the suite quick


@pytest.fixture(autouse=True)
def _clean_cache():
    engine.clear_cache()
    yield


# --------------------------------------------------------------------------
# W03-2  build_snapshots
# --------------------------------------------------------------------------
def test_single_snapshot():
    actual, nominal, phases = engine.build_snapshots(FAST)
    assert len(actual) == len(nominal) == len(phases) == 1
    assert actual[0].shape == (16, 2)


def test_snapshot_count_follows_the_config():
    actual, _, _ = engine.build_snapshots(FAST.with_(n_snapshots=4, strategy="shapes"))
    assert len(actual) == 4


def test_repeat_strategy_produces_identical_snapshots():
    actual, _, _ = engine.build_snapshots(FAST.with_(n_snapshots=3, strategy="repeat"))
    np.testing.assert_allclose(actual[0], actual[1])
    np.testing.assert_allclose(actual[0], actual[2])


@pytest.mark.parametrize("strategy", ["shift", "rotate", "shapes"])
def test_diverse_strategies_produce_different_snapshots(strategy):
    actual, _, _ = engine.build_snapshots(
        FAST.with_(n_snapshots=3, strategy=strategy)
    )
    assert not np.allclose(actual[0], actual[1]), f"{strategy} gave identical snapshots"


def test_without_errors_actual_equals_nominal():
    actual, nominal, phases = engine.build_snapshots(FAST)
    np.testing.assert_allclose(actual[0], nominal[0])
    np.testing.assert_allclose(phases[0], 0.0)


def test_position_error_separates_actual_from_nominal():
    """
    The whole reason both lists exist. `nominal` is where the beamformer thinks
    the drones are; `actual` is where they are. Without that split, coherent gain
    cannot detect anything.
    """
    actual, nominal, _ = engine.build_snapshots(FAST.with_(sigma_pos_lambda=0.5))
    assert not np.allclose(actual[0], nominal[0])


def test_position_error_is_interpreted_in_wavelengths():
    """
    sigma_pos_lambda is in WAVELENGTHS; uavsense wants METRES. Getting this wrong
    by a factor of 30 makes errors look harmless, which reads as a physics
    mystery rather than the units bug it is.
    """
    cfg = FAST.with_(sigma_pos_lambda=1.0, seed=0)
    actual, nominal, _ = engine.build_snapshots(cfg)
    lam = cfg.to_scenario().wavelength
    spread = np.std(actual[0] - nominal[0])
    assert spread == pytest.approx(lam, rel=0.5), (
        f"displacement {spread:.4f} m should be about one wavelength ({lam:.4f} m)"
    )


def test_dropping_drones_shrinks_the_formation():
    actual, nominal, phases = engine.build_snapshots(FAST.with_(n_drop=3))
    assert actual[0].shape == (13, 2)
    assert nominal[0].shape == (13, 2)
    assert len(phases[0]) == 13


def test_seed_makes_runs_reproducible():
    a, _, _ = engine.build_snapshots(FAST.with_(sigma_pos_lambda=0.5, seed=42))
    b, _, _ = engine.build_snapshots(FAST.with_(sigma_pos_lambda=0.5, seed=42))
    c, _, _ = engine.build_snapshots(FAST.with_(sigma_pos_lambda=0.5, seed=43))
    np.testing.assert_allclose(a[0], b[0])
    assert not np.allclose(a[0], c[0])


# --------------------------------------------------------------------------
# W03-3  run
# --------------------------------------------------------------------------
def test_run_returns_a_populated_result():
    r = engine.run(FAST)
    assert r.image.shape == (101, 101)
    assert r.axis.shape == (101,)
    assert r.image.max() == pytest.approx(1.0)
    assert r.metrics.res_x > 0
    assert r.n_coarray > 0
    assert r.compute_ms > 0


def test_run_rejects_an_invalid_config():
    with pytest.raises((ValidationError, ValueError)):
        engine.run(FAST.with_(formation="square", n_uav=20))


def test_result_carries_its_config_and_scenario():
    r = engine.run(FAST.with_(label="mine"))
    assert r.config.label == "mine"
    assert r.scenario.n_uav == 16


def test_preview_uses_a_coarser_grid_and_is_faster():
    cfg = DEFAULT.with_(grid_points=401)
    t0 = time.perf_counter(); full = engine.run(cfg); t_full = time.perf_counter() - t0
    engine.clear_cache()
    t0 = time.perf_counter(); prev = engine.run(cfg, preview=True); t_prev = time.perf_counter() - t0

    assert prev.image.shape[0] < full.image.shape[0]
    assert prev.preview is True and full.preview is False
    assert t_prev < t_full


def test_preview_and_full_broadly_agree():
    """A coarse preview may be less precise, but it must not tell a different
    story — otherwise the picture changes when the user lets go of the slider."""
    cfg = DEFAULT.with_(formation="ring", grid_points=401)
    assert engine.run(cfg, preview=True).metrics.res_y == pytest.approx(
        engine.run(cfg).metrics.res_y, rel=0.15
    )


def test_known_physics_survives_the_engine():
    """The square's ghost must still be there after passing through your layer."""
    r = engine.run(DEFAULT.with_(formation="square", ura_enabled=False))
    assert r.metrics.pslr_y > -8.0
    assert r.n_coarray == 49


def test_repeat_snapshots_give_coarray_gain_of_one():
    r = engine.run(FAST.with_(n_snapshots=3, strategy="repeat"))
    assert r.coarray_gain == pytest.approx(1.0)


def test_diverse_snapshots_give_coarray_gain_above_one():
    r = engine.run(FAST.with_(n_snapshots=2, strategy="shapes"))
    assert r.coarray_gain > 1.5


def test_coherence_cost_downweights_later_snapshots():
    off = engine.run(FAST.with_(n_snapshots=3, strategy="shapes",
                                apply_coherence_cost=False))
    on = engine.run(FAST.with_(n_snapshots=3, strategy="shapes",
                               apply_coherence_cost=True, drone_speed=0.5))
    assert off.weights == pytest.approx([1.0, 1.0, 1.0])
    assert on.weights[-1] < 1.0
    assert on.morph_times[-1] > 0


def test_peak_gain_responds_to_position_error():
    """Only works if `nominal` was passed through to measure()."""
    assert engine.run(FAST).metrics.peak_gain == pytest.approx(1.0, abs=1e-6)
    assert engine.run(FAST.with_(sigma_pos_lambda=0.5, seed=1)).metrics.peak_gain < 0.6


# --------------------------------------------------------------------------
# W03-4  caching
# --------------------------------------------------------------------------
def test_second_identical_run_comes_from_cache():
    first = engine.run(FAST)
    second = engine.run(FAST)
    assert first.from_cache is False
    assert second.from_cache is True


def test_cached_result_is_the_same_result():
    a = engine.run(FAST)
    b = engine.run(FAST)
    np.testing.assert_allclose(a.image, b.image)
    assert a.metrics.res_x == b.metrics.res_x


def test_cache_is_much_faster():
    cfg = DEFAULT.with_(grid_points=401)
    t0 = time.perf_counter(); engine.run(cfg); cold = time.perf_counter() - t0
    t0 = time.perf_counter(); engine.run(cfg); warm = time.perf_counter() - t0
    assert warm < cold * 0.25


def test_renaming_does_not_invalidate_the_cache():
    """The reason cache_key excludes the label."""
    engine.run(FAST.with_(label="before"))
    assert engine.run(FAST.with_(label="after")).from_cache is True


def test_changing_physics_does_invalidate_the_cache():
    engine.run(FAST)
    assert engine.run(FAST.with_(n_uav=25)).from_cache is False


def test_preview_and_full_are_cached_separately():
    """They have different grids, so one must never be served for the other."""
    engine.run(FAST, preview=True)
    full = engine.run(FAST, preview=False)
    assert full.from_cache is False


def test_cache_stats_track_hits_and_misses():
    engine.clear_cache()
    engine.run(FAST); engine.run(FAST); engine.run(FAST.with_(n_uav=25))
    s = engine.cache_stats()
    assert s["hits"] == 1 and s["misses"] == 2 and s["entries"] >= 2


def test_clear_cache_empties_it():
    engine.run(FAST)
    engine.clear_cache()
    assert engine.cache_stats()["entries"] == 0
    assert engine.run(FAST).from_cache is False


# --------------------------------------------------------------------------
# W03-5  cost estimate
# --------------------------------------------------------------------------
def test_cost_estimate_is_positive_and_ordered():
    small = engine.estimate_cost(DEFAULT.with_(grid_points=101))
    large = engine.estimate_cost(DEFAULT.with_(grid_points=401))
    assert 0 < small < large


def test_cost_estimate_grows_with_snapshots():
    one = engine.estimate_cost(DEFAULT.with_(n_snapshots=1))
    four = engine.estimate_cost(DEFAULT.with_(n_snapshots=4))
    assert four > one * 2


def test_cost_estimate_is_roughly_right():
    """Within a factor of 5 of reality — enough to make a preview decision."""
    cfg = DEFAULT.with_(grid_points=301)
    engine.clear_cache()
    predicted = engine.estimate_cost(cfg)
    t0 = time.perf_counter(); engine.run(cfg); actual = time.perf_counter() - t0
    assert predicted / 5 < max(actual, 1e-3) < predicted * 5
