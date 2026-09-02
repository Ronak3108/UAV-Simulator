"""
The figures the GUI shows.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

Each function takes a Result (or a Scenario) and returns a matplotlib Figure.
Streamlit displays one with `st.pyplot(fig)`.

WHY SEPARATE FROM app.py
------------------------
A plotting function that takes data and returns a Figure can be tested, reused in
the export module, and called from a script. A plotting function tangled into GUI
code can only be looked at. Keep them apart and your Week 11 "export a PDF report"
task becomes an afternoon instead of a rewrite.

THE STYLE IS GIVEN. Use `use_style()` and `PALETTE` so every panel looks like it
belongs to the same instrument. The palette below is colourblind-safe (checked for
deuteranopia and tritanopia separation) and survives greyscale printing — do not
swap in matplotlib's default cycle, whose green and orange are nearly identical to
a red-green colourblind reader.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "use_style", "PALETTE", "INK", "MUTED", "GRID",
    "plot_formation", "plot_coarray", "plot_psf_image", "plot_psf_cuts",
    "plot_ura_pattern", "plot_snapshot_sequence", "plot_metric_bars",
    "plot_sweep", "plot_comparison",
]

PALETTE = ["#2a6fb5", "#d4711f", "#3f9b7a", "#a4529c",
           "#8a8f45", "#b5495b", "#4d7d9b", "#9a6b3f"]
INK, MUTED, GRID = "#1c1c1a", "#6b6b66", "#dcdcd6"


def use_style() -> None:
    """Apply the project matplotlib style. Call once when the app starts. GIVEN."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 10,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "legend.frameon": False,
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
    })


# ---------------------------------------------------------------------------
def plot_formation(result, ax=None, show_ura: bool = True):
    """
    Drone positions. With show_ura, annotate how many elements each carries.

    TODO(W05-1): Implement.
      - scatter snapshot 0; if there are several, draw the later ones fainter
        (alpha 0.35) so the morph is visible in one picture
      - equal aspect, limits from the aperture, labelled axes in metres
      - with show_ura, a corner annotation: "4x4 URA, 16 elements each,
        256 total"

      A NICE TOUCH once it works: draw each drone as a small square scaled to its
      URA's physical size rather than a dot. It is not to scale with the spacing
      between drones — 4.5 cm against 13 m — so say so in the caption, but it
      makes the two-level structure obvious at a glance.
    """
    raise NotImplementedError("TODO(W05-1) in simulator/plotting.py")


def plot_coarray(result, ax=None):
    """
    The fused co-array, with its point count and gain in the title.

    TODO(W05-2): Implement.
      - small markers (s=9), some transparency, they overlap heavily
      - title: "co-array: 133 points (gain 2.71x)"
      - when n_snapshots > 1, colour by which snapshot contributed the point.
        That single choice turns the plot into the argument the project is
        making: the user SEES the second formation filling the first one's gaps.
    """
    raise NotImplementedError("TODO(W05-2) in simulator/plotting.py")


def plot_psf_image(result, ax=None, dyn_range_db: float = 40.0):
    """
    The PSF as a 2-D dB image — the money shot of the whole app.

    TODO(W05-3): Implement.
      - 20*log10 of the image, clipped at -dyn_range_db
      - `extent` from result.axis so the axes read in metres, origin="lower"
      - a SEQUENTIAL colormap ("magma" or "viridis"), never a rainbow: this is one
        magnitude going from low to high, and a rainbow invents visual boundaries
        that are not in the data
      - colorbar labelled "dB", and turn the grid off over an image
      - FIX the colour scale to (-dyn_range_db, 0). If it rescales per config the
        user cannot compare two runs, which defeats the point of a simulator.
    """
    raise NotImplementedError("TODO(W05-3) in simulator/plotting.py")


def plot_psf_cuts(result, ax=None, direction: str = "both"):
    """
    Horizontal and/or vertical cut through the PSF centre, in dB.

    TODO(W05-4): Implement.
      - x cut is image[G//2, :], y cut is image[:, G//2]
      - 20*log10(np.maximum(cut, 1e-6)) — the np.maximum guards log10(0) at a
        perfect null, which gives -inf and makes matplotlib silently drop the line
      - fixed ylim (-60, 3) so runs are comparable
      - dotted line at -3 dB so resolution is readable straight off the plot
      - annotate the measured PSLR

      WORTH DOING: mark the predicted grating-lobe position, lambda*R/d for the
      current spacing. When the user increases drone count and watches the ghost
      march outward and off the plot, the physics explains itself.
    """
    raise NotImplementedError("TODO(W05-4) in simulator/plotting.py")


def plot_ura_pattern(scenario, ax=None, cut: str = "az"):
    """
    One drone's URA pattern over a wide angle — what the element sliders do.

    TODO(W06-1): Implement in week 6, when you add the URA controls.
      - uavsense.ura.ura_pattern_cut(scenario, axis=cut, half_angle_deg=90)
      - plot in dB against angle
      - mark the 3 dB beamwidth from scenario.ura.beamwidth_deg
      - if scenario.ura.grating_lobe_angle_deg() is not None, mark it in the
        warning colour and label it

      THE POINT OF THIS PANEL: the swarm-level and drone-level pictures look
      similar but are on completely different scales — metres versus centimetres,
      fractions of a degree versus tens of degrees. Put the scale in the title so
      nobody confuses them.
    """
    raise NotImplementedError("TODO(W06-1) in simulator/plotting.py")


def plot_snapshot_sequence(result, ax=None):
    """
    All snapshots overlaid, colour-coded, with arrows showing which drone flies
    where between them.

    TODO(W08-1): Implement in week 8.
      - one colour per snapshot from PALETTE
      - uavsense.costs.assignment(a, b) gives the optimal drone-to-slot matching;
        use it for the arrows or they will cross over each other and look like
        chaos rather than a manoeuvre
      - title with total morph time and the coherence weight of the last snapshot
    """
    raise NotImplementedError("TODO(W08-1) in simulator/plotting.py")


def plot_metric_bars(results, ax=None, metric: str = "pslr_y"):
    """
    Bar chart of one metric across several results. For the comparison view.

    TODO(W10-1): Implement in week 10.
      - handle nan (a config with no sidelobe in the window) by drawing a hatched
        bar and labelling it "none in window" rather than silently plotting zero
      - direct-label each bar with its value; a bar chart the reader has to
        measure against an axis is a bar chart doing half its job
    """
    raise NotImplementedError("TODO(W10-1) in simulator/plotting.py")


def plot_sweep(results, parameter: str, metric: str, ax=None):
    """
    One metric against the swept parameter — the output of engine.sweep.

    TODO(W11-2): Implement in week 11.
      - x from each result's config field, y from its metrics
      - markers ON the line: these are measured points, not a continuous function,
        and the reader should be able to see how many there are
      - for a resolution sweep, overlay the lambda*R/(2D) prediction as a dashed
        line. Watching measurement sit on theory is the most convincing plot the
        app can produce.
    """
    raise NotImplementedError("TODO(W11-2) in simulator/plotting.py")


def plot_comparison(result_a, result_b, figsize=(11, 7)):
    """
    Side-by-side A/B figure: formations, co-arrays, PSFs, cuts overlaid.

    TODO(W10-2): Implement in week 10. Build it from the single-panel functions
    above rather than duplicating their bodies — that is exactly why they each
    take an `ax`.

      The bottom row should overlay both PSF cuts on ONE axis rather than showing
      two separate plots. Comparison means putting the lines on top of each other;
      two adjacent plots make the reader do the work.
    """
    raise NotImplementedError("TODO(W10-2) in simulator/plotting.py")
