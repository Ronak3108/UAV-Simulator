"""
simulator — the interactive application layer. THIS IS WHAT YOU BUILD.

    state.py      SimConfig: the whole app state as one frozen value
    engine.py     SimConfig -> Result, with caching and a preview mode
    plotting.py   Result -> matplotlib figures
    presets.py    save / load / built-in configurations
    export.py     CSV, PNG, report bundles
    compare.py    A/B comparison of two configurations
    app.py        the Streamlit GUI

THE ARCHITECTURE RULE
---------------------
    app.py  ->  engine.py  ->  uavsense
       |            |
       +-> state.py +-> plotting.py

The GUI never imports uavsense directly. It builds a SimConfig and asks the
engine. Keep that boundary and every layer below the GUI is testable without a
browser — which is why the test suite can check your work at all.
"""

__version__ = "0.1.0"
