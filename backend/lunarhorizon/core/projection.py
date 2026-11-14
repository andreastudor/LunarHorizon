"""Proiecția stereografică polară sudică pe sferă (docs/SPEC_FIZICA.md §3.3).

Parametrii impliciți sunt provizorii (deciziile D-05 și D-06): se confirmă din metadatele fiecărui
GeoTIFF la etapa E05. Ei coincid cu `IAU_2015:30135` din PROJ 9.7.1, dar echivalența cu CRS-ul
fișierelor PGDA nu este presupusă.

    rho = 2·R·k0·tan(45° + lat/2),   x = rho·sin(lon - lon0),   y = rho·cos(lon - lon0)
    k   = 2·k0 / (1 - sin(lat))
"""

import math
from dataclasses import dataclass

from lunarhorizon.core.conventions import REFERENCE_RADIUS_M, ConventionStatus
from lunarhorizon.core.coords import (
    CoordinateError,
    validate_latitude_deg,
    wrap_longitude_deg,
)
from lunarhorizon.core.units import deg_to_rad, rad_to_deg


@dataclass(frozen=True)
class SouthPolarStereographic:
    radius_m: float = REFERENCE_RADIUS_M
    central_meridian_deg: float = 0.0
    scale_factor: float = 1.0
    status: ConventionStatus = "provisional"

    def forward(self, latitude_deg: float, longitude_deg: float) -> tuple[float, float]:
        """(lat, lon) → (x_m, y_m). Polul nord nu este reprezentabil."""
        validate_latitude_deg(latitude_deg)
        if latitude_deg == 90.0:
            raise CoordinateError("latitude_out_of_range", latitude_deg)
        rho = (
            2.0
            * self.radius_m
            * self.scale_factor
            * math.tan(math.pi / 4.0 + deg_to_rad(latitude_deg) / 2.0)
        )
        delta = deg_to_rad(longitude_deg - self.central_meridian_deg)
        return rho * math.sin(delta), rho * math.cos(delta)

    def inverse(self, x_m: float, y_m: float) -> tuple[float, float]:
        """(x_m, y_m) → (lat, lon). În origine (polul sud), longitudinea este meridianul central."""
        if not (math.isfinite(x_m) and math.isfinite(y_m)):
            raise CoordinateError("not_finite", (x_m, y_m))
        rho = math.hypot(x_m, y_m)
        latitude_deg = -90.0 + 2.0 * rad_to_deg(
            math.atan(rho / (2.0 * self.radius_m * self.scale_factor))
        )
        longitude_deg = self.central_meridian_deg + rad_to_deg(math.atan2(x_m, y_m))
        return latitude_deg, wrap_longitude_deg(longitude_deg)

    def scale(self, latitude_deg: float) -> float:
        """Factorul de scară local: distanța în plan / distanța pe sferă."""
        return 2.0 * self.scale_factor / (1.0 - math.sin(deg_to_rad(latitude_deg)))

    def to_proj4(self) -> str:
        return (
            f"+proj=stere +lat_0=-90 +lon_0={self.central_meridian_deg!r} "
            f"+k={self.scale_factor!r} +x_0=0 +y_0=0 +R={self.radius_m!r} +units=m +no_defs"
        )
