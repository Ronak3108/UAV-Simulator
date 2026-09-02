#!/usr/bin/env python3
"""
Week 1 — see what the physics library already does, before you build anything.

    python scripts/demo_physics.py

Nothing here is a task. This script exists so that on day one you can see the
whole system working from the command line, and know exactly what your GUI has to
put a face on.

Writes four figures to figures/.
"""
import sys
from pathlib import Path
from dataclasses import replace

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uavsense import BASE, URA, get_formation, measure, unique_coarray   # noqa: E402
from uavsense.imaging import point_spread_function, coherent_gain        # noqa: E402
from uavsense.coarray import fused_coarray, coarray_gain                 # noqa: E402
from uavsense.errors import position_jitter                              # noqa: E402
from uavsense.sequences import build_sequence                            # noqa: E402
from uavsense.ura import ura_pattern_cut                                 # noqa: E402
from simulator.plotting import use_style, PALETTE, MUTED                 # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
OUT.mkdir(exist_ok=True)
NO_URA = replace(BASE, ura=URA(enabled=False))


def banner(t):
    print("\n" + "=" * 72 + f"\n  {t}\n" + "=" * 72)


def main():
    use_style()
    print(BASE.summary())

    # ---------------------------------------------------------------- 1
    banner("1. Formation shape barely changes resolution, but hugely changes ghosts")
    print(f"{'shape':<10}{'co-array':>9}{'res_x':>8}{'res_y':>8}"
          f"{'PSLR_x':>9}{'PSLR_y':>9}")
    print("-" * 53)
    shapes = ["square", "ring", "diamond", "x", "spiral"]
    for name in shapes:
        P = get_formation(name, 16, 40.0)
        m = measure([P], NO_URA)
        print(f"{name:<10}{len(unique_coarray(P)):>9}{m.res_x:>8.3f}"
              f"{m.res_y:>8.3f}{m.pslr_x:>9.1f}{m.pslr_y:>9.1f}")
    print("\n  Resolution spans 0.81-1.16 m: a factor of 1.4.")
    print("  Cross-range PSLR spans -0.2 to -25.7 dB.")
    print("  Square and diamond are both LATTICES, and both make ghosts.")
    print("  Ring, X and spiral are aperiodic, and do not.")
    print("  -> the question is not 'which shape', it is 'is it periodic'.")

    fig, ax = plt.subplots(2, 4, figsize=(11, 5.4))
    for j, name in enumerate(shapes[:4]):
        P = get_formation(name, 16, 40.0)
        ax[0, j].scatter(P[:, 0], P[:, 1], s=40, color=PALETTE[j],
                         edgecolor="white", linewidth=1.1)
        ax[0, j].set_title(name); ax[0, j].set_aspect("equal")
        ax[0, j].set_xlim(-26, 26); ax[0, j].set_ylim(-26, 26)
        V = unique_coarray(P)
        ax[1, j].scatter(V[:, 0], V[:, 1], s=8, color=PALETTE[j], alpha=0.7)
        ax[1, j].set_title(f"co-array: {len(V)}", fontsize=9, color=MUTED)
        ax[1, j].set_aspect("equal")
        ax[1, j].set_xlim(-26, 26); ax[1, j].set_ylim(-26, 26)
    fig.suptitle("Formations and their MIMO sum co-arrays", y=1.0)
    fig.tight_layout(); fig.savefig(OUT / "demo1_formations.png"); plt.close(fig)

    # ---------------------------------------------------------------- 2
    banner("2. The per-drone URA: gain and beamwidth, but NOT resolution")
    print(f"{'URA':<10}{'elements':>10}{'gain dB':>9}{'beam deg':>10}"
          f"{'res_y':>8}")
    print("-" * 47)
    for n in [1, 2, 4, 8, 16, 32]:
        sc = replace(BASE, ura=URA(n_x=n, n_y=n, enabled=n > 1))
        m = measure([get_formation("ring", 16, 40.0)], sc)
        bw = sc.ura.beamwidth_deg(sc.wavelength)[0]
        print(f"{n}x{n:<7}{sc.total_elements:>10}{sc.array_gain_db:>9.1f}"
              f"{bw:>10.1f}{m.res_y:>8.3f}")
    print("\n  Gain climbs 30 dB from 1x1 to 32x32. Resolution does not move.")
    print("  Resolution is the SWARM's job; the URA only collects more signal")
    print("  and narrows how much sky each drone sees.")
    print("  Your GUI users will expect otherwise. Tell them.")

    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8))
    for j, n in enumerate([2, 4, 8, 16]):
        sc = replace(BASE, ura=URA(n_x=n, n_y=n))
        a, p = ura_pattern_cut(sc, half_angle_deg=90)
        ax[0].plot(a, 20 * np.log10(np.maximum(p, 1e-4)), color=PALETTE[j],
                   linewidth=1.7, label=f"{n}x{n}")
    ax[0].set_xlabel("angle from boresight [deg]")
    ax[0].set_ylabel("URA response [dB]"); ax[0].set_ylim(-40, 3)
    ax[0].legend(fontsize=8); ax[0].set_title("More elements -> narrower drone beam")

    for j, s in enumerate([0.5, 0.75, 1.0, 1.5]):
        sc = replace(BASE, ura=URA(n_x=8, n_y=8, spacing_wavelengths=s))
        a, p = ura_pattern_cut(sc, half_angle_deg=90)
        ax[1].plot(a, 20 * np.log10(np.maximum(p, 1e-4)), color=PALETTE[j],
                   linewidth=1.7, label=f"{s} lambda")
    ax[1].set_xlabel("angle from boresight [deg]"); ax[1].set_ylim(-40, 3)
    ax[1].legend(fontsize=8)
    ax[1].set_title("Spacing > lambda/2 -> the URA grows its OWN ghosts")
    fig.tight_layout(); fig.savefig(OUT / "demo2_ura.png"); plt.close(fig)

    # ---------------------------------------------------------------- 3
    banner("3. Multi-snapshot: diversity buys information, repetition does not")
    sq = get_formation("square", 16, 40.0)
    print(f"{'strategy':<28}{'co-array':>10}{'gain':>7}{'PSLR_x':>9}{'PSLR_y':>9}")
    print("-" * 63)
    for label, seq in [
        ("1 snapshot", [sq]),
        ("2 identical (repeat)", build_sequence(sq, "repeat", 2, 40.0)),
        ("2 with half-spacing shift", build_sequence(sq, "shift", 2, 40.0)),
        ("2 rotated", build_sequence(sq, "rotate", 2, 40.0)),
        ("2 different shapes", build_sequence(sq, "shapes", 2, 40.0)),
        ("4 different shapes", build_sequence(sq, "shapes", 4, 40.0)),
    ]:
        m = measure(seq, NO_URA)
        print(f"{label:<28}{len(fused_coarray(seq)):>10}"
              f"{coarray_gain(seq):>7.2f}{m.pslr_x:>9.1f}{m.pslr_y:>9.1f}")
    print("\n  'repeat' gives gain exactly 1.00 and changes nothing at all.")
    print("  Diversity is what buys information, not the number of snapshots.")
    print("  Note shift helps ground range while shape-swap helps cross range:")
    print("  different defects need different remedies. That trade-off is")
    print("  exactly what makes an interactive simulator worth building.")

    # ---------------------------------------------------------------- 4
    banner("4. The trap your GUI must not fall into")
    P = get_formation("ring", 16, 40.0)
    lam = BASE.wavelength
    print(f"{'sigma':>10}{'mm':>8}{'coherent gain':>15}{'PSLR_x dB':>12}")
    print("-" * 45)
    gains, sigmas = [], [0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0]
    for s in sigmas:
        g = np.mean([coherent_gain([position_jitter(P, s * lam,
                     np.random.default_rng(t))], nominal=[P], scenario=NO_URA)
                     for t in range(40)])
        m = measure([position_jitter(P, s * lam, np.random.default_rng(0))], NO_URA)
        gains.append(g)
        print(f"{s:>10.2f}{s*lam*1000:>8.1f}{g:>15.3f}{m.pslr_x:>12.1f}")
    print("\n  Coherent gain collapses 1.00 -> 0.06. PSLR barely moves.")
    print("  The image is normalised by its own peak, so PSLR cannot see this.")
    print("  Half the gain is gone by ~3 mm of position error.")
    print("  Plain GPS gives metres. THIS NEEDS RADIO RANGING, NOT GPS.")
    print("  Show BOTH numbers in your GUI or it will mislead its user.")

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(sigmas, gains, "o-", color=PALETTE[0], linewidth=1.9, markersize=6)
    ax.axhline(1 / 16, color=MUTED, linestyle=":", linewidth=1.2)
    ax.text(0.06, 1 / 16 * 1.3, "incoherent floor (1/N)", fontsize=8, color=MUTED)
    ax.set_xscale("symlog", linthresh=0.05)
    ax.set_xlabel(r"position error $\sigma$ [wavelengths]")
    ax.set_ylabel("coherent gain at focus"); ax.set_ylim(0, 1.05)
    ax.set_title("What position error actually destroys")
    fig.tight_layout(); fig.savefig(OUT / "demo3_coherence.png"); plt.close(fig)

    # ---------------------------------------------------------------- 5
    axis, img = point_spread_function([sq], NO_URA)
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    im = ax[0].imshow(20 * np.log10(np.maximum(img, 1e-5)), origin="lower",
                      cmap="magma", vmin=-40, vmax=0,
                      extent=[axis[0], axis[-1], axis[0], axis[-1]])
    ax[0].set_title("4x4 square: the ghost at 1.31 m")
    ax[0].set_xlabel("ground range [m]"); ax[0].set_ylabel("cross range [m]")
    ax[0].grid(False)
    plt.colorbar(im, ax=ax[0], fraction=0.046, label="dB")

    c = NO_URA.grid_points // 2
    for j, name in enumerate(["square", "ring", "x"]):
        _, im2 = point_spread_function([get_formation(name, 16, 40.0)], NO_URA)
        ax[1].plot(axis, 20 * np.log10(np.maximum(im2[:, c], 1e-6)),
                   color=PALETTE[j], linewidth=1.7, label=name)
    ax[1].set_ylim(-60, 3); ax[1].set_xlabel("cross range [m]")
    ax[1].set_ylabel("response [dB]"); ax[1].legend(fontsize=8)
    ax[1].set_title("Only the lattice has a ghost")
    fig.tight_layout(); fig.savefig(OUT / "demo4_psf.png"); plt.close(fig)

    banner("Figures written to figures/")
    for p in sorted(OUT.glob("demo*.png")):
        print(f"  {p.name}")
    print("\nThat is everything the physics library does.")
    print("Your job is to put a face on it. Start with TASKS.md, Week 2.")


if __name__ == "__main__":
    main()
