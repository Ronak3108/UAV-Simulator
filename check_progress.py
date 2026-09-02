#!/usr/bin/env python3
"""
What is left to build.

    python check_progress.py            summary by week
    python check_progress.py --list     every outstanding task with its location
    python check_progress.py --week 04  just one week
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

TAG = re.compile(r"TODO\((W(\d{2})-[0-9a-z]+)\)")
SKIP = {".git", "__pycache__", ".pytest_cache", "_reference", ".venv", "venv"}

WEEKS = {
    "W02": ("SimConfig — the configuration model", "week02"),
    "W03": ("The engine — snapshots, caching, cost", "week03"),
    "W04": ("First working GUI  <- the milestone", None),
    "W05": ("All the panels and plots", None),
    "W06": ("URA controls and error panel", None),
    "W08": ("Snapshot builder", None),
    "W09": ("Presets", "week09"),
    "W10": ("A/B comparison", None),
    "W11": ("Sweeps and export", "week11"),
    "W12": ("Polish, animation, performance", None),
}


def scan(root: Path):
    found = defaultdict(list)
    for path in sorted(root.rglob("*.py")):
        if any(p in SKIP for p in path.parts) or path.name == "check_progress.py":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            m = TAG.search(line)
            if m:
                text = line.split(":", 1)[-1].strip() if ":" in line else ""
                found[m.group(2)].append(
                    (m.group(1), path.relative_to(root), i, text[:64])
                )
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--week")
    args = ap.parse_args()

    root = Path(__file__).parent
    found = scan(root)

    if not found:
        print("\n  No TODOs left. The simulator is complete.\n")
        print("  Final checks:")
        print("    pytest -q")
        print("    streamlit run simulator/app.py\n")
        return

    total = sum(len(v) for v in found.values())
    print(f"\n  {total} tasks outstanding\n")
    print(f"  {'Week':<8}{'Left':>5}   Topic")
    print("  " + "-" * 58)
    for wk in sorted(found):
        if args.week and wk != args.week.zfill(2):
            continue
        name = WEEKS.get(f"W{wk}", ("", None))[0]
        print(f"  Week {wk:<4}{len(found[wk]):>5}   {name}")

    nxt = min(found)
    label, marker = WEEKS.get(f"W{nxt}", ("", None))
    print("\n  " + "-" * 58)
    print(f"  Next up: Week {nxt} — {label}")
    if marker:
        print(f"  Run:     pytest -m {marker} -v")
    else:
        print("  No test file for this week — check it by USING the app.")
    print()

    if args.list:
        for wk in sorted(found):
            if args.week and wk != args.week.zfill(2):
                continue
            print(f"\n  === Week {wk} " + "=" * 46)
            for tag, path, line, text in found[wk]:
                print(f"  {tag:<9} {path}:{line}")
                if text:
                    print(f"            {text}")
        print()


if __name__ == "__main__":
    main()
