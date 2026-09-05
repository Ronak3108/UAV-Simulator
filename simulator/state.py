"""
The configuration model — one object describing everything the user set.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

WHY THIS FILE COMES FIRST
-------------------------
It is tempting to start with the GUI, wire sliders straight to physics calls, and
watch pictures appear. Do not. That design fails in week 3 for reasons that are
completely predictable:

  - you cannot save or load a configuration, because there is no single object
    that IS the configuration
  - you cannot cache, because there is no hashable key
  - you cannot compare two setups, because "the setup" is scattered across
    twenty Streamlit widget values
  - you cannot write a test, because testing means launching a browser

Get this object right and all four problems disappear. `SimConfig` is the whole
state of the app: one frozen, hashable, serialisable value. Widgets produce it,
the engine consumes it, presets store it, the comparison view holds two of them.

THE RULE: the GUI never talks to `uavsense` directly. It builds a `SimConfig` and
hands it to the engine. Keep that boundary and you can test everything without a
browser.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict, fields
from typing import Any

from uavsense.config import Scenario, URA

import uavsense.formations

__all__ = ["SimConfig", "ValidationError", "DEFAULT"]


class ValidationError(ValueError):
    """Raised when a configuration cannot physically be built."""


@dataclass(frozen=True)
class SimConfig:
    """
    Everything the user chose, in one immutable value.

    Frozen on purpose. An immutable config can be a dict key (so caching works),
    can be compared with `==` (so you can skip recomputation), and cannot be
    mutated behind the engine's back halfway through a run.

    To change one field:  new = replace(cfg, n_uav=25)
    """

    # ---- swarm -------------------------------------------------------------
    formation: str = "square"
    n_uav: int = 16
    aperture: float = 40.0

    # ---- per-drone URA -----------------------------------------------------
    ura_enabled: bool = True
    ura_nx: int = 4
    ura_ny: int = 4
    ura_spacing: float = 0.5        # wavelengths
    ura_steer_az: float = 0.0       # degrees
    ura_steer_el: float = 0.0       # degrees

    # ---- geometry ----------------------------------------------------------
    f0_ghz: float = 10.0
    altitude: float = 300.0
    ground_range: float = 500.0

    # ---- snapshots ---------------------------------------------------------
    n_snapshots: int = 1
    strategy: str = "repeat"
    shift_fraction: float = 0.5
    rotate_total_deg: float = 90.0

    # ---- errors ------------------------------------------------------------
    sigma_pos_lambda: float = 0.0   # position error, in wavelengths
    sigma_phase_rad: float = 0.0
    n_drop: int = 0
    seed: int = 0

    # ---- coherence cost ----------------------------------------------------
    apply_coherence_cost: bool = False
    drone_speed: float = 5.0        # m/s
    allan_dev: float = 1e-11

    # ---- imaging grid ------------------------------------------------------
    grid_half_width: float = 2.5
    grid_points: int = 401

    # ---- bookkeeping -------------------------------------------------------
    label: str = "untitled"

    # =======================================================================
    # TODO(W02-1): to_scenario()
    # =======================================================================
    def to_scenario(self) -> Scenario:
        """
        Translate this config into the `Scenario` the physics library wants.

        TODO(W02-1): Implement this. It is the single most important method in
        the file — the bridge between "what the user clicked" and "what the
        physics needs".

          - build a `URA(...)` from the ura_* fields
          - build a `Scenario(...)` from the rest
          - remember f0 is stored in GHz here and Scenario wants Hz

        Keep it a pure function: no validation, no side effects, no printing.
        Validation belongs in `validate()` so the GUI can show a friendly message
        before anything expensive runs.
        """

        # An URA object is defined with the values.
        ura = URA(
            n_x = self.ura_nx,
            n_y = self.ura_ny,
            spacing_wavelengths = self.ura_spacing,
            steer_az_deg = self.ura_steer_az,
            steer_el_deg = self.ura_steer_el,
            enabled = self.ura_enabled
        )

        # A Scenario object is defined as well. It takes an URA object as well for an argument (I guess, we call it that).
        scenario = Scenario(
            f0 = self.f0_ghz * 1e9,
            n_uav = self.n_uav,
            altitude = self.altitude,
            ground_range = self.ground_range,
            aperture = self.aperture,
            ura = ura,
            grid_half_width = self.grid_half_width,
            grid_points = self.grid_points
        )

        # The function returns scenario object.
        return scenario
    
        raise NotImplementedError("TODO(W02-1) in simulator/state.py")

    # =======================================================================
    # TODO(W02-2): validate()
    # =======================================================================
    def validate(self) -> list[str]:
        """
        Return a list of human-readable problems. Empty list means the config is
        fine.

        Return messages rather than raising: the GUI wants to show ALL the
        problems at once next to the offending widgets, not die on the first one.

        TODO(W02-2): Implement these checks. Write the messages for a user, not
        for yourself — "Square formation needs a perfect square number of drones
        (16 or 25, not 20)" beats "invalid n_uav".

          - n_uav must be legal for the chosen formation
            (uavsense.formations.valid_count does the check;
             nearest_valid_count gives you the number to suggest)
          - n_uav >= 2, and warn above ~64 (the PSF gets slow)
          - aperture > 0
          - ura_nx, ura_ny >= 1; warn above 32
          - ura_spacing > 0; warn above 0.5, because that is where the URA itself
            starts producing grating lobes
          - n_snapshots >= 1
          - strategy must be in uavsense.sequences.SEQUENCE_STRATEGIES
          - n_drop < n_uav (you cannot drop every drone)
          - grid_points odd and >= 51; warn above 801 (slow)
          - altitude and ground_range > 0

        A GOOD EXTRA once the basics work: separate hard ERRORS from soft
        WARNINGS. "25 drones with a 32x32 URA is 25600 elements and will take a
        few seconds" is worth saying without blocking the run.
        """

        # Defining the list that contains all the problems.

        problem_list = []

        # Starting to check for potential problems.

        if(not(uavsense.formations.valid_count(self.formation, self.n_uav))):
            suggestion = uavsense.formations.nearest_valid_count(self.formation, self.n_uav)
            problem_list.append(f"The Number of UAVs provided for {self.formation} Formation is incorrect. Try changing Number of UAVs to {suggestion}.")

        if(self.n_uav < 2):
            problem_list.append("The UAV count should not be less than 2.")

        if(self.n_uav > 64):
            problem_list.append("The UAV count should not be above 64 as it slows down PSF.")

        if(self.aperture <= 0):
            problem_list.append("Aperture must be greater than 0.")

        if(self.ura_nx < 1 or self.ura_nx > 32):
            problem_list.append("Please keep the number of elements across the drone in X direction from 1 to 32.")

        if(self.ura_ny < 1 or self.ura_ny > 32):
            problem_list.append("Please keep the number of elements across the drone in Y direction from 1 to 32.")

        if(self.ura_spacing <= 0):
            problem_list.append("Please keep Spacing (URA) between 0 and 0.5 as if it goes above 0.5, URA will start producing grating lobes.")

        if(self.n_snapshots < 1):
            problem_list.append("Snapshot count can't be less than 1.")

        if(self.strategy not in uavsense.sequences.SEQUENCE_STRATEGIES):
            problem_list.append("Invalid Strategy is Used.")

        if(self.n_drop >= self.n_uav):
            problem_list.append("You can't drop all Drones or more Drones than you have.")

        if(self.grid_points % 2 == 0):
            problem_list.append("Number of grid points can't be EVEN.")
        
        if(self.grid_points < 51):
            problem_list.append("Number of Grid Points should be at least 51.")
        elif(self.grid_points > 801):
            problem_list.append("Number of Grid points being above 801 will result in slow processing.")

        if(self.altitude <= 0):
            problem_list.append("Altitude can't be a negative value.")

        if(self.ground_range <= 0):
            problem_list.append("Ground Range can't be negative.")


        return problem_list

        raise NotImplementedError("TODO(W02-2) in simulator/state.py")

    def is_valid(self) -> bool:
        """True if `validate()` found nothing. Given — do not change."""
        return not self.validate()

    # =======================================================================
    # TODO(W02-3): serialisation
    # =======================================================================
    def to_dict(self) -> dict[str, Any]:
        """
        Plain dict, JSON-safe. Used by presets, export and the URL state.

        TODO(W02-3a): Implement. `dataclasses.asdict` does almost all of it.
        Add a "version" key — you WILL change these fields in week 8, and a
        preset saved in week 5 should still load rather than crash.
        """

        sim_dict = asdict(self)
        sim_dict.update({'version': 1})

        return sim_dict

        raise NotImplementedError("TODO(W02-3a) in simulator/state.py")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SimConfig":
        """
        Rebuild from a dict, tolerating older and newer files.

        TODO(W02-3b): Implement. The requirement that matters: a preset saved by
        an older version must still load. So IGNORE unknown keys rather than
        raising, and let missing keys fall back to the dataclass default.

            known = {f.name for f in dataclasses.fields(cls)}
            return cls(**{k: v for k, v in d.items() if k in known})

        Round-tripping is tested: from_dict(to_dict(cfg)) == cfg.
        """

        known_keys = {f.name for f in fields(cls)}     # This will give me the list of attributes of SimConfig Class that are present in that version.

        sim_args = {}
        for key, value in d.items():
            if(key in known_keys):
                sim_args.update({key: value})           # We only pass known arguments, other we skip or we let the default values be assigned.

        return cls(**sim_args)

        raise NotImplementedError("TODO(W02-3b) in simulator/state.py")

    # =======================================================================
    # TODO(W03-1): cache key
    # =======================================================================
    def cache_key(self) -> tuple:
        """
        A hashable key identifying everything that changes the RESULT.

        TODO(W03-1): Implement this in week 3, when you build the engine.

        The subtlety that makes it worth its own method: `label` must NOT be part
        of the key. Renaming a configuration does not change its physics, and if
        the label is in the key then typing in the name box throws away the cache
        and recomputes on every keystroke.

        Ask of every field: "if I change this, does the output change?" If no, it
        stays out of the key. That is the whole design.
        """
        raise NotImplementedError("TODO(W03-1) in simulator/state.py")

    # ---- convenience, given ------------------------------------------------
    def with_(self, **kwargs) -> "SimConfig":
        """Copy with fields replaced: cfg.with_(n_uav=25)."""
        return replace(self, **kwargs)

    def describe(self) -> str:
        """One-line summary for a plot title or a comparison table."""
        ura = (
            f"{self.ura_nx}x{self.ura_ny} URA" if self.ura_enabled else "single element"
        )
        snap = (
            f"{self.n_snapshots} snapshots ({self.strategy})"
            if self.n_snapshots > 1 else "1 snapshot"
        )
        return f"{self.formation}, {self.n_uav} drones, {ura}, {snap}"


DEFAULT = SimConfig()
