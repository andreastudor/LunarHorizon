"""Direcțiile Soarelui și Pământului văzute dintr-un punct lunar (docs/SPEC_FIZICA.md §4-§5).

Observatorul are poziție constantă în cadrul lunar fix ME: r = (R + h_suprafață + h_observator) · u.
`spkcpo` întoarce vectorul observator → corp exprimat în același cadru ME, evaluat la epoca
observatorului (refloc = OBSERVER). Proiecția pe baza E, N, U folosește funcțiile din `core`.

Corecții: `NONE` (geometric) sau aparent. Corecția aparentă implicită este `CN+S` (D-02,
confirmată de astronomi, comunicată de utilizator; `core.conventions.APPARENT_CORRECTION`).
`LT+S` rămâne pentru diagnostic. Niciuna nu include devierea gravitațională a luminii sau un
model de atmosferă.
"""

import math
from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
import spiceypy

from lunarhorizon.astro.kernels import SPICE_LOCK, LoadedProfile, activate
from lunarhorizon.astro.timeconv import require_in_coverage, utc_to_et
from lunarhorizon.core.conventions import (
    APPARENT_CORRECTION,
    REFERENCE_RADIUS_M,
    Correction,
)
from lunarhorizon.core.coords import (
    AzimuthConvention,
    Vec3,
    az_el_from_enu,
    azimuth_convention,
    geographic_to_me,
    me_to_enu,
    normalize_longitude_deg,
    validate_latitude_deg,
)
from lunarhorizon.core.units import M_PER_KM, rad_to_deg
from lunarhorizon.core.utc import canonical_utc

Body = Literal["sun", "earth"]

# D-02: aceeași valoare ca `core.conventions.APPARENT_CORRECTION` (nu se definește a doua oară).
DEFAULT_APPARENT_CORRECTION: Final[Correction] = APPARENT_CORRECTION
SPICE_BODY_NAMES: Final[dict[Body, str]] = {"sun": "SUN", "earth": "EARTH"}
# Sub această componentă orizontală a versorului, azimutul nu este definit (zenit sau nadir).
UNDEFINED_AZIMUTH_HORIZONTAL: Final = 1e-12


@dataclass(frozen=True)
class ObserverSite:
    """Punct lunar cu altitudini explicite. Nu există valori implicite pentru altitudine."""

    latitude_deg: float
    longitude_deg: float
    surface_height_m: float
    observer_height_m: float

    def __post_init__(self) -> None:
        validate_latitude_deg(self.latitude_deg)
        object.__setattr__(self, "longitude_deg", normalize_longitude_deg(self.longitude_deg))
        if not (math.isfinite(self.surface_height_m) and math.isfinite(self.observer_height_m)):
            raise ValueError("altitudinile trebuie să fie numere finite")
        if self.observer_height_m < 0.0:
            raise ValueError("înălțimea observatorului nu poate fi negativă")

    def position_me_m(self, radius_m: float = REFERENCE_RADIUS_M) -> Vec3:
        height = self.surface_height_m + self.observer_height_m
        return geographic_to_me(self.latitude_deg, self.longitude_deg, height, radius_m)


@dataclass(frozen=True)
class BodyDirection:
    body: Body
    correction: Correction
    profile_id: str
    frame_id: str
    utc: str
    et: float
    # `None` la zenit sau nadir, unde azimutul nu este definit.
    azimuth_deg: float | None
    elevation_deg: float
    distance_km: float
    light_time_s: float
    angular_radius_deg: float
    direction_enu: Vec3
    azimuth_convention: AzimuthConvention


def az_el_or_undefined(direction_enu: Vec3) -> tuple[float | None, float]:
    """Azimut (sau `None` la zenit/nadir) și elevație, pentru un vector ENU nenul."""
    e, n, u = direction_enu
    length = math.hypot(e, n, u)
    horizontal = math.hypot(e, n)
    elevation_deg = rad_to_deg(math.atan2(u, horizontal))
    if horizontal <= UNDEFINED_AZIMUTH_HORIZONTAL * length:
        return None, elevation_deg
    azimuth_deg, _ = az_el_from_enu(direction_enu)
    return azimuth_deg, elevation_deg


_RADII_KM: dict[tuple[str, Body], float] = {}


def body_radius_km(body: Body, profile: LoadedProfile) -> float:
    """Raza ecuatorială din kernelul PCK text al profilului (pck00011); memorată pe profil."""
    key = (profile.profile_id, body)
    cached = _RADII_KM.get(key)
    if cached is not None:
        return cached
    with SPICE_LOCK:
        activate(profile)
        _, radii = spiceypy.bodvrd(SPICE_BODY_NAMES[body], "RADII", 3)
    _RADII_KM[key] = float(radii[0])
    return _RADII_KM[key]


def _observer_km(site: ObserverSite, radius_m: float) -> np.ndarray:
    return np.array(site.position_me_m(radius_m)) / M_PER_KM


def body_direction(
    profile: LoadedProfile,
    site: ObserverSite,
    body: Body,
    utc: str,
    correction: Correction = DEFAULT_APPARENT_CORRECTION,
    radius_m: float = REFERENCE_RADIUS_M,
) -> BodyDirection:
    canonical = canonical_utc(utc)
    et = utc_to_et(canonical, profile)
    require_in_coverage(et, profile)
    return body_direction_et(profile, site, body, et, canonical, correction, radius_m)


def body_direction_et(
    profile: LoadedProfile,
    site: ObserverSite,
    body: Body,
    et: float,
    utc_label: str,
    correction: Correction = DEFAULT_APPARENT_CORRECTION,
    radius_m: float = REFERENCE_RADIUS_M,
) -> BodyDirection:
    """Același calcul ca `body_direction`, la un ET dat (scanarea evenimentelor, E10).

    Acoperirea efemeridelor se verifică de apelant pentru capetele intervalului."""
    with SPICE_LOCK:
        state, light_time_s = spiceypy.spkcpo(
            SPICE_BODY_NAMES[body],
            et,
            profile.frame_id,
            "OBSERVER",
            correction,
            _observer_km(site, radius_m),
            "MOON",
            profile.frame_id,
        )
    position_km = np.asarray(state[:3], dtype=float)
    distance_km = float(np.linalg.norm(position_km))
    unit = position_km / distance_km
    direction_enu = me_to_enu(
        (float(unit[0]), float(unit[1]), float(unit[2])), site.latitude_deg, site.longitude_deg
    )
    azimuth_deg, elevation_deg = az_el_or_undefined(direction_enu)
    radius_km = body_radius_km(body, profile)
    return BodyDirection(
        body=body,
        correction=correction,
        profile_id=profile.profile_id,
        frame_id=profile.frame_id,
        utc=utc_label,
        et=et,
        azimuth_deg=azimuth_deg,
        elevation_deg=elevation_deg,
        distance_km=distance_km,
        light_time_s=float(light_time_s),
        angular_radius_deg=rad_to_deg(math.asin(radius_km / distance_km)),
        direction_enu=direction_enu,
        azimuth_convention=azimuth_convention(site.latitude_deg),
    )


def body_vector_icrf_km(
    profile: LoadedProfile,
    site: ObserverSite,
    body: Body,
    et: float,
    correction: Correction = "NONE",
    radius_m: float = REFERENCE_RADIUS_M,
) -> np.ndarray:
    """Vectorul observator → corp, în km, în cadrul J2000 al SPICE (realizarea ICRF a JPL)."""
    require_in_coverage(et, profile)
    activate(profile)
    with SPICE_LOCK:
        state, _ = spiceypy.spkcpo(
            SPICE_BODY_NAMES[body],
            et,
            "J2000",
            "OBSERVER",
            correction,
            _observer_km(site, radius_m),
            "MOON",
            profile.frame_id,
        )
    return np.asarray(state[:3], dtype=float)
