"""
The GUI. THIS IS THE MAIN DELIVERABLE OF THE PROJECT.

    streamlit run simulator/app.py

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

HOW STREAMLIT WORKS, because everything below depends on understanding it
------------------------------------------------------------------------
Streamlit re-runs this ENTIRE FILE, top to bottom, every time the user touches
any widget. There is no event loop and there are no callbacks in the usual sense.
A slider does not "fire an event"; it changes a value and the script runs again.

Three consequences that shape the whole design:

  1. Anything expensive must be CACHED or it runs on every keystroke. This is why
     engine.py has a cache and why SimConfig is hashable.

  2. Anything that must survive a re-run lives in `st.session_state`, a dict that
     persists across runs. Local variables do not survive.

  3. Widget order IS layout order. The script reads top to bottom like the page.

BUILD IT IN THIS ORDER
----------------------
Week 4 is deliberately the smallest thing that works end to end: three sliders and
one plot. Resist adding more until that runs. A working ugly app you extend for
eight weeks beats a beautiful architecture you demo in week 12.

    Week 4   sidebar with formation / n_uav / aperture, one PSF image      <- milestone
    Week 5   all the panels, tabs, the metrics row
    Week 6   URA controls and the drone-pattern panel
    Week 8   snapshot builder
    Week 9   presets
    Week 10  A/B comparison
    Week 11  sweeps and export
    Week 12  polish, animation, performance
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st                                    # noqa: E402

from simulator.state import SimConfig, DEFAULT            # noqa: E402
from simulator import engine, plotting                    # noqa: E402
from uavsense.formations import (                         # noqa: E402
    list_formations, FORMATION_CONSTRAINTS, valid_count, nearest_valid_count,
)
from uavsense.sequences import SEQUENCE_STRATEGIES, describe_strategy  # noqa: E402


# ===========================================================================
# TODO(W04-1): page setup
# ===========================================================================
def setup_page() -> None:
    """
    st.set_page_config plus one-time initialisation.

    TODO(W04-1): Implement.
      - st.set_page_config(page_title=..., layout="wide", page_icon=...)
        MUST be the first Streamlit call in the script or Streamlit errors.
      - "wide" matters: the default centred layout wastes half the screen and
        this app is all plots.
      - call plotting.use_style() once
      - seed st.session_state with defaults if the keys are missing
    """
    raise NotImplementedError("TODO(W04-1) in simulator/app.py")


# ===========================================================================
# TODO(W04-2): the sidebar — where the user drives the simulator
# ===========================================================================
def sidebar_swarm() -> dict:
    """
    Formation, drone count, aperture. Returns the fields as a dict.

    TODO(W04-2): Implement. Start here — this is the Week 4 milestone.

      - st.selectbox for formation, options from list_formations()
      - st.slider for n_uav (4 to 64) and aperture (10 to 200 m)
      - st.number_input for f0_ghz, altitude, ground_range

      THE THING THAT MAKES IT FEEL PROFESSIONAL: square and diamond need a
      perfect square count, X needs an even one. Do NOT let the user pick 20
      drones with a square formation and get a traceback. Use valid_count() and
      nearest_valid_count() to snap the value, and show st.caption with
      FORMATION_CONSTRAINTS[name] so they know why it jumped.

      Handling that gracefully is the difference between a script with widgets
      and an application.
    """
    raise NotImplementedError("TODO(W04-2) in simulator/app.py")


def sidebar_ura() -> dict:
    """
    Per-drone URA controls.

    TODO(W06-2): Implement in week 6.
      - st.checkbox "Enable per-drone array" — unchecking it makes every drone a
        single element, which is the cleanest A/B in the whole app
      - sliders for n_x, n_y (1 to 32) and spacing (0.25 to 2.0 wavelengths)
      - sliders for steering azimuth and elevation (-60 to +60 degrees)
      - a LIVE READOUT that updates as they drag: element count, physical size in
        cm, beamwidth in degrees, total array gain in dB.
        scenario.ura.beamwidth_deg() and .aperture_m() give you these.

      WARN when spacing goes above 0.5: that is where the URA grows its own
      grating lobes. scenario.ura.grating_lobe_angle_deg() tells you where. Use
      st.warning so it is visible without blocking.

      SET AN EXPECTATION for whoever uses this: more URA elements give more GAIN
      and a NARROWER drone beam, but they do NOT improve resolution — resolution
      is the swarm's job. Users will expect otherwise and be confused. A one-line
      st.caption saying so is worth more than another slider.
    """
    raise NotImplementedError("TODO(W06-2) in simulator/app.py")


def sidebar_snapshots() -> dict:
    """
    Snapshot count and diversity strategy.

    TODO(W08-2): Implement in week 8.
      - st.slider for n_snapshots (1 to 8)
      - st.selectbox for strategy from SEQUENCE_STRATEGIES, with
        describe_strategy(kind) as the help text
      - strategy-dependent controls: shift_fraction only for "shift",
        rotate_total_deg only for "rotate". Showing irrelevant controls is how a
        panel becomes noise.
      - a checkbox for the coherence cost, with drone speed and Allan deviation
        behind it

      WHAT TO SHOW THE USER: when n_snapshots > 1, display the co-array gain
      prominently. Watching it sit at exactly 1.00 for "repeat" and jump to 2.71
      for "shapes" is the central lesson of the project, delivered by the app
      rather than by a paragraph.
    """
    raise NotImplementedError("TODO(W08-2) in simulator/app.py")


def sidebar_errors() -> dict:
    """
    Position error, phase error, dropped drones.

    TODO(W06-3): Implement in week 6.
      - sliders for sigma_pos in WAVELENGTHS (0 to 2), sigma_phase in radians
        (0 to pi), n_drop (0 to n_uav-1), and a seed number_input
      - show sigma_pos in millimetres too: 0.1 lambda reads as harmless until you
        see it is 3 mm

      THE PANEL THAT TEACHES THE MOST IN THE WHOLE APP: put coherent gain right
      next to PSLR here. Drag the position error slider and watch gain collapse
      from 1.00 to 0.2 while PSLR barely moves. Two metrics, same experiment,
      opposite conclusions — and the reason the app must show both.
    """
    raise NotImplementedError("TODO(W06-3) in simulator/app.py")


def build_config() -> SimConfig:
    """
    Assemble one SimConfig from every sidebar section.

    TODO(W04-3): Implement. Call the sidebar functions, merge their dicts,
    construct SimConfig(**merged).

    Then run config.validate() and, if it returns anything, show the problems
    with st.error and st.stop(). Stopping here is right: better a clear message
    than a traceback from deep inside numpy.
    """
    raise NotImplementedError("TODO(W04-3) in simulator/app.py")


# ===========================================================================
# TODO(W05-5): the main panels
# ===========================================================================
def show_metrics_row(result) -> None:
    """
    The headline numbers across the top: st.metric in st.columns.

    TODO(W05-5): Implement.
      - resolution x and y in metres, PSLR x and y in dB, coherent gain,
        co-array points
      - st.metric takes a `delta` argument — pass the change against the previous
        run (keep it in session_state) and the user gets instant feedback on
        whether their last tweak helped
      - format nan as "none in window", not "nan"
    """
    raise NotImplementedError("TODO(W05-5) in simulator/app.py")


def show_main_tabs(result) -> None:
    """
    The plots, in tabs.

    TODO(W05-6): Implement with st.tabs.
      Suggested: "PSF" | "Formation" | "Co-array" | "Drone array" | "Snapshots"

      Tabs matter for a reason specific to Streamlit: everything in every tab is
      computed on every re-run, but only the visible one is rendered. So keep the
      expensive figure (the PSF image) in the first tab and make sure the others
      are cheap, or the app pays for panels nobody is looking at.
    """
    raise NotImplementedError("TODO(W05-6) in simulator/app.py")


def show_status_bar(result) -> None:
    """
    Compute time, cache hit rate, preview-vs-full, element count.

    TODO(W05-7): Implement, in st.sidebar at the bottom or an st.expander.

    This is a debugging tool you are building for yourself. When the app feels
    slow in week 11, this bar tells you whether you are missing the cache or
    genuinely computing too much — and those have completely different fixes.
    """
    raise NotImplementedError("TODO(W05-7) in simulator/app.py")


def show_preset_controls() -> SimConfig | None:
    """
    Load / save / delete presets. Returns a config if one was loaded.

    TODO(W09-3): Implement in week 9.
      - selectbox of presets.list_presets(), with the built-in description shown
      - Load applies it: write the values into st.session_state and st.rerun()
      - a text box and Save button for the current config
      - Delete, offered only for user presets

      THE STREAMLIT GOTCHA that will cost you an hour: you cannot set a widget's
      value directly after it has been created. Loading a preset means writing
      into session_state and calling st.rerun() so the widgets rebuild from the
      new state. Use `key=` on every widget so they read from session_state.
    """
    raise NotImplementedError("TODO(W09-3) in simulator/app.py")


def show_comparison_view() -> None:
    """
    A/B mode: pin the current config, change something, see both.

    TODO(W10-4): Implement in week 10.
      - a "Pin this configuration" button storing the config in session_state
      - when something is pinned, show compare.compare(pinned, current)
      - a diff caption listing what changed, from compare.diff_configs
      - the comparison table, with an arrow marking which direction is better
    """
    raise NotImplementedError("TODO(W10-4) in simulator/app.py")


def show_sweep_view() -> None:
    """
    Sweep one parameter and plot the curve.

    TODO(W11-6): Implement in week 11.
      - selectbox for which parameter, inputs for start / stop / steps
      - a Run button — NEVER run a sweep automatically on script re-run, or the
        app will launch a twenty-point sweep every time someone types a character
      - st.progress driven by the engine's progress callback
      - plotting.plot_sweep, plus a download button for the CSV
    """
    raise NotImplementedError("TODO(W11-6) in simulator/app.py")


# ===========================================================================
# TODO(W04-4): main
# ===========================================================================
def main() -> None:
    """
    Wire it together.

    TODO(W04-4): Implement. Week 4 version is deliberately tiny:

        setup_page()
        config = build_config()
        result = engine.run(config)
        st.pyplot(plotting.plot_psf_image(result))

    That is the milestone: sliders on the left, a PSF that changes when you move
    them. Get THAT working end to end before adding a single tab. Everything
    after is decoration on a thing that already works.

    The full version grows into:
        setup_page()
        loaded = show_preset_controls()
        config = loaded or build_config()
        result = engine.run(config, preview=engine.estimate_cost(config) > 0.5)
        show_metrics_row(result)
        show_main_tabs(result)
        show_comparison_view()
        show_sweep_view()
        show_status_bar(result)
    """
    raise NotImplementedError("TODO(W04-4) in simulator/app.py")


if __name__ == "__main__":
    main()
