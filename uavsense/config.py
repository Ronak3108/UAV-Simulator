"""
Scenario and array parameters.

PART OF THE GIVEN PHYSICS LIBRARY — complete and tested. You do not edit this.
You will, however, import `Scenario` and `URA` constantly, so read this file once.

Everything downstream reads its numbers from a Scenario object, so your GUI's job
is essentially: collect widget values -> build a Scenario -> hand it to the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
import numpy as np

C_LIGHT = 299_792_458.0

__all__ = ["Scenario", "URA", "BASE", "BASE_URA", "C_LIGHT"]


@dataclass(frozen=True)
class URA:
    """
    The uniform rectangular array carried by ONE drone.

    Each drone is not a single antenna: it carries an n_x by n_y grid of elements
    with `spacing` between them, and it can steer that sub-array electronically.

    Two levels of array, then:
      - the SWARM (drones tens of metres apart) sets resolution and grating lobes
      - the URA on each drone (elements centimetres apart) sets how much sky that
        drone illuminates, and how much gain it contributes

    The two levels multiply. See uavsense.ura for the maths.
    """

    n_x: int = 4                    # elements across the drone, x
    n_y: int = 4                    # elements across the drone, y
    spacing_wavelengths: float = 0.5   # element spacing, in wavelengths
    steer_az_deg: float = 0.0       # electronic steering, azimuth, from boresight
    steer_el_deg: float = 0.0       # electronic steering, elevation, from boresight
    enabled: bool = True            # False -> every drone is a single isotropic antenna

    @property
    def n_elements(self) -> int:
        """Elements per drone."""
        return self.n_x * self.n_y if self.enabled else 1

    def aperture_m(self, wavelength: float) -> tuple[float, float]:
        """Physical size of one drone's array, in metres."""
        d = self.spacing_wavelengths * wavelength
        return ((self.n_x - 1) * d, (self.n_y - 1) * d)

    def beamwidth_deg(self, wavelength: float) -> tuple[float, float]:
        """
        3 dB beamwidth of one drone's URA, in degrees.

        0.886 * lambda / (n * d), using the EFFECTIVE aperture n*d rather than the
        physical (n-1)*d — that is the standard convention for a uniform array and
        it matches the measured pattern to about 1% for n >= 8. With lambda/2
        spacing it comes out near 102/n degrees.
        """
        if not self.enabled:
            return (180.0, 180.0)
        d = self.spacing_wavelengths * wavelength

        def bw(n: int) -> float:
            if n <= 1:
                return 180.0
            return float(np.degrees(0.886 * wavelength / (n * d)))

        return (bw(self.n_x), bw(self.n_y))

    @property
    def grating_lobe_free(self) -> bool:
        """True if element spacing <= lambda/2, so the URA has no grating lobes."""
        return self.spacing_wavelengths <= 0.5 + 1e-9

    def grating_lobe_angle_deg(self) -> float | None:
        """
        Angle of the URA's first grating lobe from boresight, or None if there is
        none. Appears once element spacing exceeds lambda/2:  sin(theta) = lambda/d.
        """
        if self.grating_lobe_free:
            return None
        s = 1.0 / self.spacing_wavelengths
        return float(np.degrees(np.arcsin(s))) if s <= 1.0 else None


@dataclass(frozen=True)
class Scenario:
    """One complete radar scenario. Frozen — use `replace()` to vary a parameter."""

    f0: float = 10e9              # carrier frequency [Hz] (X-band)
    n_uav: int = 16               # number of drones
    altitude: float = 300.0       # flight height above ground [m]
    ground_range: float = 500.0   # horizontal distance to scene centre [m]
    aperture: float = 40.0        # bounding width of the formation [m]

    ura: URA = URA()              # the array carried by each drone

    # Imaging grid.
    #
    # WIDTH matters for correctness: the window must be wide enough to contain
    # the real sidelobes, or a "PSLR" is really just the value at the grid edge.
    #
    # DENSITY barely matters for the metrics. Measured across 101 to 401 points,
    # resolution and PSLR agree to about 1% — the extra samples only make the
    # displayed image look smoother. Cost scales as grid_points squared, so
    # 401 costs 16x what 101 does and buys almost nothing numerically. 201 is
    # the sweet spot for a live GUI; raise it for a figure you are exporting.
    grid_half_width: float = 2.5  # patch is +/- this many metres
    grid_points: int = 201        # samples per side (odd, so a sample sits at 0)

    # ---- derived quantities -------------------------------------------------
    @property
    def wavelength(self) -> float:
        return C_LIGHT / self.f0

    @property
    def wavenumber(self) -> float:
        return 2.0 * np.pi / self.wavelength

    @property
    def slant_range(self) -> float:
        return float(np.hypot(self.altitude, self.ground_range))

    @property
    def look_angle_deg(self) -> float:
        """Angle from vertical (nadir) down to the scene centre."""
        return float(np.degrees(np.arctan2(self.ground_range, self.altitude)))

    @property
    def resolution_scale(self) -> float:
        """
        lambda*R/(2D) — the resolution SCALE of this geometry, in metres.

        A rule of thumb, not a hard bound: a measured 3 dB width can land a little
        either side of it. Use it as a sanity check — a result twice as good as
        this is a bug.
        """
        return self.wavelength * self.slant_range / (2.0 * self.aperture)

    @property
    def total_elements(self) -> int:
        """Every antenna element in the whole swarm."""
        return self.n_uav * self.ura.n_elements

    @property
    def array_gain_db(self) -> float:
        """
        Two-way coherent array gain relative to one isotropic element, in dB.

        The swarm contributes N^2 (MIMO, so squared) and each drone's URA
        contributes its own element count squared on top.
        """
        return float(20 * np.log10(max(self.total_elements, 1)))

    def summary(self) -> str:
        bw_x, bw_y = self.ura.beamwidth_deg(self.wavelength)
        ap_x, ap_y = self.ura.aperture_m(self.wavelength)
        return (
            f"f0 = {self.f0/1e9:.2f} GHz   lambda = {self.wavelength*100:.2f} cm\n"
            f"swarm: {self.n_uav} drones over {self.aperture:.0f} m "
            f"({self.aperture/self.wavelength:.0f} wavelengths)\n"
            f"per drone: {self.ura.n_x}x{self.ura.n_y} URA at "
            f"{self.ura.spacing_wavelengths:.2f} lambda "
            f"= {ap_x*100:.1f} x {ap_y*100:.1f} cm, "
            f"beamwidth {bw_x:.1f} x {bw_y:.1f} deg\n"
            f"total elements: {self.total_elements}   "
            f"two-way array gain: {self.array_gain_db:.1f} dB\n"
            f"altitude {self.altitude:.0f} m, ground range {self.ground_range:.0f} m "
            f"-> slant range {self.slant_range:.1f} m, "
            f"look angle {self.look_angle_deg:.1f} deg\n"
            f"resolution scale lambda*R/(2D) = {self.resolution_scale:.3f} m"
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Scenario":
        d = dict(d)
        if isinstance(d.get("ura"), dict):
            d["ura"] = URA(**d["ura"])
        return cls(**d)


#: Default scenario — import this everywhere.
BASE = Scenario()
BASE_URA = BASE.ura


if __name__ == "__main__":
    print(BASE.summary())
