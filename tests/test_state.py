"""
Week 2 — SimConfig. The spec for simulator/state.py.

Run:  pytest -m week02 -v
"""
import dataclasses
import pytest

from simulator.state import SimConfig, DEFAULT
from uavsense.config import Scenario, URA

pytestmark = pytest.mark.week02


# --------------------------------------------------------------------------
# W02-1  to_scenario
# --------------------------------------------------------------------------
def test_to_scenario_returns_a_scenario():
    assert isinstance(DEFAULT.to_scenario(), Scenario)


def test_frequency_is_converted_from_ghz_to_hz():
    """Stored in GHz for the GUI, needed in Hz by the physics."""
    assert SimConfig(f0_ghz=10.0).to_scenario().f0 == pytest.approx(10e9)
    assert SimConfig(f0_ghz=24.0).to_scenario().f0 == pytest.approx(24e9)


def test_swarm_fields_reach_the_scenario():
    sc = SimConfig(n_uav=25, aperture=60.0, altitude=400.0,
                   ground_range=800.0).to_scenario()
    assert (sc.n_uav, sc.aperture, sc.altitude, sc.ground_range) == (25, 60.0, 400.0, 800.0)


def test_ura_fields_reach_the_scenario():
    sc = SimConfig(ura_nx=8, ura_ny=4, ura_spacing=0.75,
                   ura_steer_az=10.0, ura_steer_el=-5.0).to_scenario()
    assert isinstance(sc.ura, URA)
    assert (sc.ura.n_x, sc.ura.n_y) == (8, 4)
    assert sc.ura.spacing_wavelengths == pytest.approx(0.75)
    assert sc.ura.steer_az_deg == pytest.approx(10.0)
    assert sc.ura.steer_el_deg == pytest.approx(-5.0)


def test_disabling_the_ura_carries_through():
    sc = SimConfig(ura_enabled=False, ura_nx=8, ura_ny=8).to_scenario()
    assert sc.ura.enabled is False
    assert sc.total_elements == sc.n_uav      # one element each


def test_grid_settings_carry_through():
    sc = SimConfig(grid_half_width=5.0, grid_points=201).to_scenario()
    assert sc.grid_half_width == pytest.approx(5.0)
    assert sc.grid_points == 201


def test_to_scenario_is_pure():
    """No mutation, no surprises: same input, same output, config untouched."""
    cfg = SimConfig(n_uav=16)
    before = dataclasses.asdict(cfg)
    cfg.to_scenario(); cfg.to_scenario()
    assert dataclasses.asdict(cfg) == before


# --------------------------------------------------------------------------
# W02-2  validate
# --------------------------------------------------------------------------
def test_default_config_is_valid():
    assert DEFAULT.validate() == []
    assert DEFAULT.is_valid()


def test_validate_returns_strings_not_exceptions():
    problems = SimConfig(formation="square", n_uav=20).validate()
    assert isinstance(problems, list)
    assert problems and all(isinstance(p, str) for p in problems)


def test_square_rejects_non_square_counts():
    assert SimConfig(formation="square", n_uav=20).validate()
    assert SimConfig(formation="square", n_uav=16).validate() == []
    assert SimConfig(formation="square", n_uav=25).validate() == []


def test_diamond_rejects_non_square_counts():
    assert SimConfig(formation="diamond", n_uav=20).validate()


def test_x_rejects_odd_counts():
    assert SimConfig(formation="x", n_uav=15).validate()
    assert SimConfig(formation="x", n_uav=16).validate() == []


def test_ring_accepts_any_count():
    for n in (5, 7, 20, 31):
        assert SimConfig(formation="ring", n_uav=n).validate() == []


def test_error_message_is_useful():
    """A user must be able to act on it. Naming the field is the minimum."""
    msg = " ".join(SimConfig(formation="square", n_uav=20).validate()).lower()
    assert "square" in msg or "drone" in msg or "20" in msg


@pytest.mark.parametrize("bad", [
    dict(n_uav=1),
    dict(aperture=0.0),
    dict(aperture=-10.0),
    dict(n_snapshots=0),
    dict(strategy="teleport"),
    dict(ura_nx=0),
    dict(ura_spacing=0.0),
    dict(n_drop=16),            # cannot drop every drone
    dict(altitude=0.0),
    dict(ground_range=-5.0),
    dict(grid_points=10),       # too coarse
])
def test_invalid_configurations_are_caught(bad):
    assert SimConfig(**bad).validate(), f"should have been rejected: {bad}"


@pytest.mark.parametrize("ok", [
    dict(formation="ring", n_uav=7),
    dict(n_snapshots=8, strategy="shapes"),
    dict(ura_enabled=False, ura_nx=1, ura_ny=1),
    dict(n_drop=3),
    dict(ura_spacing=1.5),      # legal, though it grows grating lobes
])
def test_valid_configurations_are_accepted(ok):
    assert SimConfig(**ok).validate() == [], f"should have been accepted: {ok}"


# --------------------------------------------------------------------------
# W02-3  serialisation
# --------------------------------------------------------------------------
def test_to_dict_is_json_safe():
    import json
    json.dumps(DEFAULT.to_dict())       # must not raise


def test_to_dict_carries_a_version():
    """Fields will change in week 8; an old preset must still load."""
    assert "version" in DEFAULT.to_dict()


def test_round_trip_is_exact():
    cfg = SimConfig(formation="x", n_uav=24, aperture=55.0, ura_nx=8,
                    n_snapshots=3, strategy="shapes", label="test")
    assert SimConfig.from_dict(cfg.to_dict()) == cfg


def test_unknown_keys_are_ignored():
    """A preset written by a NEWER version must still load in an older one."""
    d = DEFAULT.to_dict()
    d["a_field_from_the_future"] = 42
    assert SimConfig.from_dict(d) == DEFAULT


def test_missing_keys_fall_back_to_defaults():
    """A preset written by an OLDER version must still load."""
    assert SimConfig.from_dict({"n_uav": 25}).n_uav == 25
    assert SimConfig.from_dict({"n_uav": 25}).aperture == DEFAULT.aperture


# --------------------------------------------------------------------------
# W03-1  cache key
# --------------------------------------------------------------------------
def test_cache_key_is_hashable():
    hash(DEFAULT.cache_key())
    {DEFAULT.cache_key(): 1}


def test_identical_configs_share_a_key():
    assert SimConfig(n_uav=16).cache_key() == SimConfig(n_uav=16).cache_key()


def test_label_is_not_part_of_the_key():
    """
    THE point of having this method. The label does not change the physics, and
    if it is in the key then typing in the name box recomputes on every keystroke.
    """
    a = SimConfig(label="first")
    b = SimConfig(label="a completely different name")
    assert a.cache_key() == b.cache_key()


@pytest.mark.parametrize("field,value", [
    ("formation", "ring"), ("n_uav", 25), ("aperture", 60.0),
    ("ura_nx", 8), ("ura_ny", 8), ("ura_spacing", 1.0), ("ura_enabled", False),
    ("ura_steer_az", 15.0), ("f0_ghz", 24.0), ("altitude", 500.0),
    ("ground_range", 900.0), ("n_snapshots", 3), ("strategy", "shapes"),
    ("sigma_pos_lambda", 0.5), ("sigma_phase_rad", 1.0), ("n_drop", 2),
    ("seed", 7), ("grid_points", 201), ("grid_half_width", 5.0),
    ("apply_coherence_cost", True),
])
def test_every_physical_field_changes_the_key(field, value):
    """If changing a field changes the result, it must change the cache key."""
    assert DEFAULT.cache_key() != DEFAULT.with_(**{field: value}).cache_key(), (
        f"changing {field} did not change the cache key — stale results ahead"
    )


# --------------------------------------------------------------------------
# Given helpers
# --------------------------------------------------------------------------
def test_config_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT.n_uav = 99


def test_with_returns_a_modified_copy():
    assert DEFAULT.with_(n_uav=25).n_uav == 25
    assert DEFAULT.n_uav == 16


def test_describe_mentions_the_essentials():
    d = SimConfig(formation="ring", n_uav=25, n_snapshots=3).describe()
    assert "ring" in d and "25" in d and "3" in d
