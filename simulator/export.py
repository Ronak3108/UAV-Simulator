"""
Getting results out of the app.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

Anything a user cannot export did not really happen. Every number the app shows
should be extractable, and every figure downloadable, with the parameters that
produced it attached.

THE RULE THAT MATTERS: a result file without its parameters is worthless three
weeks later. Always write provenance alongside the numbers.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

__all__ = ["result_to_csv", "results_to_csv", "figure_to_png_bytes",
           "export_bundle", "provenance"]


def provenance(config) -> dict:
    """
    The metadata that goes beside every export: timestamp, versions, full config.

    TODO(W11-3a): Implement.
      - datetime.now().isoformat(timespec="seconds")
      - uavsense.__version__, numpy version, python version
      - config.to_dict()
      - git commit if available (subprocess "git rev-parse --short HEAD", wrapped
        in try/except — it must not crash the app when run from a zip with no
        git repo around it)
    """
    raise NotImplementedError("TODO(W11-3a) in simulator/export.py")


def result_to_csv(result, path) -> Path:
    """
    One result to CSV, plus a .json sidecar holding the provenance.

    TODO(W11-3b): Implement. result.summary_row() gives you the row.
    """
    raise NotImplementedError("TODO(W11-3b) in simulator/export.py")


def results_to_csv(results, path) -> Path:
    """
    Many results (a sweep, or a comparison set) to one CSV.

    TODO(W11-3c): Implement. Rows may not all share keys, so take the union of
    the columns and leave missing cells empty rather than crashing.
    """
    raise NotImplementedError("TODO(W11-3c) in simulator/export.py")


def figure_to_png_bytes(fig) -> bytes:
    """
    A matplotlib figure as PNG bytes, for st.download_button.

    TODO(W11-4): Implement.
      - io.BytesIO, fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
      - buf.seek(0), return buf.getvalue()

      Streamlit needs BYTES, not a path — it serves the download to a browser
      that has no access to your filesystem. This trips people up.
    """
    raise NotImplementedError("TODO(W11-4) in simulator/export.py")


def export_bundle(result, out_dir, include_figures: bool = True) -> Path:
    """
    Everything about one run into a timestamped folder: CSV, provenance JSON, the
    raw PSF as .npy, and every figure as PNG.

    TODO(W11-5): Implement. This is the "I need this for my report" button.
      - out_dir / f"{timestamp}_{config.label}" as the folder
      - return the folder path so the GUI can tell the user where it went

      FIXED FILE NAMES — the tests check these, because a bundle is a contract
      that someone reads six months later with a script:

          metrics.csv       the summary row
          provenance.json   parameters, versions, timestamp
          psf.npy           the image array, exactly as displayed
          axis.npy          the ground coordinates that go with it
          psf.png           (optional) the rendered figure

      Saving the raw array costs nothing and means someone can re-plot without
      re-running anything.

      WORTH ADDING: zip the folder and hand it back as bytes, so the browser
      download works when the app is served from somewhere other than the user's
      own machine. Writing to disk only helps when the disk is theirs.
    """
    raise NotImplementedError("TODO(W11-5) in simulator/export.py")
