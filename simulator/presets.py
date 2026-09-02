"""
Saving, loading and shipping configurations.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

A simulator nobody can save anything in is a toy. Presets are what let your
supervisor open the app, pick "4x4 square, 2 snapshots" from a dropdown, and see
the grating lobe without knowing which eleven sliders to set.

The built-in library also doubles as documentation: each preset is a worked
example of something the physics does.
"""
from __future__ import annotations

import json
from pathlib import Path

from .state import SimConfig

__all__ = ["BUILTIN", "save_preset", "load_preset", "list_presets",
           "delete_preset", "PRESET_DIR"]

PRESET_DIR = Path(__file__).resolve().parents[1] / "presets"


# ---------------------------------------------------------------------------
# TODO(W09-1)
# ---------------------------------------------------------------------------
#: Built-in configurations that ship with the app. Each is a worked example.
BUILTIN: dict[str, dict] = {
    # TODO(W09-1): Fill this in. Each entry is {"description": str, "config": dict}
    # so the GUI can show a one-line explanation beside the name.
    #
    # The set below is what makes the app teach rather than just compute. Build
    # each one, LOOK at it, and only keep the description if it matches what you
    # actually see:
    #
    #   "square-ghost"        4x4 square, 1 snapshot. The full-strength grating
    #                         lobe at 1.31 m. The default anyone would draw, and
    #                         the worst one available.
    #   "ring-clean"          Same drones on a ring. No ghost. The fix is
    #                         aperiodicity, not shape as such.
    #   "repeat-is-useless"   Square, 2 identical snapshots. Co-array gain
    #                         exactly 1.00. The null result.
    #   "shift-helps"         Square, 2 snapshots, half-spacing shift.
    #                         Ground-range PSLR -22.5 -> -30 dB.
    #   "shapes-help-more"    Square then X. Co-array 49 -> 133, and the
    #                         cross-range ghost drops.
    #   "big-ura"             16x16 elements per drone. Shows the gain and the
    #                         narrow drone beam - and that resolution does NOT
    #                         improve, because that is the swarm's job.
    #   "sparse-ura"          Element spacing 1.5 lambda. The URA grows its own
    #                         grating lobe at ~42 degrees. Two levels of array,
    #                         two independent ways to create ghosts.
    #   "gps-is-not-enough"   Position error 0.25 lambda. Coherent gain collapses
    #                         to ~0.2 while PSLR barely moves - the trap, made
    #                         into a preset.
    #   "coherence-cost"      4 snapshots with the coherence cost switched on.
    #                         More snapshots stop helping once drift dominates.
}


def list_presets() -> list[str]:
    """
    Every preset name: built-ins first, then user-saved ones from PRESET_DIR.

    TODO(W09-2a): Implement. Mark user presets distinctly in the returned names
    (or return two lists) so the GUI can group them and only offer Delete on the
    ones the user actually owns.
    """
    raise NotImplementedError("TODO(W09-2a) in simulator/presets.py")


def save_preset(name: str, config: SimConfig, overwrite: bool = False) -> Path:
    """
    Write a config to PRESET_DIR/<name>.json.

    TODO(W09-2b): Implement.
      - sanitise the name into a safe filename; a user WILL type "test 1/2" and
        you do not want that creating a directory
      - refuse to overwrite unless overwrite=True, and never let a user preset
        shadow a built-in
      - store config.to_dict() with indent=2 so the files are diffable in git
    """
    raise NotImplementedError("TODO(W09-2b) in simulator/presets.py")


def load_preset(name: str) -> SimConfig:
    """
    Load by name, checking built-ins first.

    TODO(W09-2c): Implement.
      - built-in names resolve from BUILTIN without touching the disk
      - user presets come from PRESET_DIR
      - a corrupt or hand-edited file should raise something the GUI can show as
        a message, not a raw JSONDecodeError traceback in the middle of the page

      SimConfig.from_dict already ignores unknown keys, so a preset saved before
      you added a field still loads. That is the whole reason it was written that
      way — test it by loading an old preset after adding a field in week 10.
    """
    raise NotImplementedError("TODO(W09-2c) in simulator/presets.py")


def delete_preset(name: str) -> bool:
    """
    Delete a user preset. Returns False for built-ins, which cannot be deleted.

    TODO(W09-2d): Implement.
    """
    raise NotImplementedError("TODO(W09-2d) in simulator/presets.py")
