"""Vizibilitatea Soarelui (disc extins) și a Pământului față de orizont (E10; SPEC_FIZICA §7).

Soare (D-04, confirmată de astronomi, comunicată de utilizator): vizibil dacă o porțiune cu arie
pozitivă a discului este deasupra orizontului modelat H(A). Discul are centrul (A_c, e_c) și raza
unghiulară rho = asin(R/D) din același rezultat CN+S. Se lucrează în planul tangent al cerului la
centrul discului (x = ΔA·cos e_c, y = e); aproximația are eroare relativă de ordinul rho^2
(aproximativ 2·10⁻⁵) și este documentată.

- `clearance` g = max_x [y_sus(x) - H(A(x))]: aria vizibilă este pozitivă dacă și numai dacă g > 0
  (H continuă). Contactul tangent (g = 0) nu este arie pozitivă.
- h = min_x [y_jos(x) - H(A(x))]: discul este complet deasupra dacă h > 0.
- Fracția vizibilă = aria neascunsă / aria discului (integrare pe coloane), cu incertitudine din
  rezoluția profilului (H ± ε) și din integrare. Nu este fracție de flux și nu este putere;
  eclipsele nu sunt incluse.

Pământ (criteriul documentat): vizibilitate geometrică spre centru dacă e > max(H(A), e_min).

Starea este nedeterminată (nu „ascuns”) când datele lipsesc (`no_data`), când profilul este doar o
limită inferioară (`partial_data`) și corpul nu este sigur ascuns, sau când |g| ≤ ε
(`near_threshold`), adică metoda nu poate distinge o porțiune foarte mică de un contact tangent. ε =
max(ε_numeric, rugozitatea locală a profilului), unde rugozitatea unui eșantion este abaterea lui de
la media vecinilor.
"""

import math
from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray

from lunarhorizon.contracts.horizon import HorizonProfile

# Rezoluția numerică a criteriilor (grade), mult sub T-01 (0,001°); aleasă prin teste (VALIDARE).
EPS_NUMERIC_DEG: Final = 1e-6
# Coloanele de integrare pe diametrul discului (convergență: VALIDARE, E10).
DISC_COLUMNS: Final = 128

SunState = Literal["hidden", "partially_visible", "fully_visible", "undetermined"]
EarthState = Literal["hidden", "visible", "undetermined"]
UndeterminedReason = Literal["near_threshold", "no_data", "partial_data"]
DataState = Literal["ok", "no_data", "lower_bound"]
TimelineState = Literal["visible", "hidden", "unknown"]
Cause = Literal["terrain", "idealized_horizon", "elevation_threshold"]
FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class HorizonModel:
    """H(A) liniar între eșantioane regulate în azimut, continuu la 0°/360°.

    `elevation` are NaN pentru `no_data`; `lower_bound` marchează azimuturile `partial` (H real ≥
    valoare).
    """

    def __init__(
        self,
        step_deg: float,
        elevation: FloatArray,
        lower_bound: BoolArray,
        obstacle_distance: FloatArray,
        kind: Literal["idealized", "dem"],
    ) -> None:
        self.step_deg = step_deg
        self.elevation = elevation
        self.lower_bound = lower_bound
        self.obstacle_distance = obstacle_distance
        self.kind = kind
        self.count = int(elevation.size)
        neighbours = (np.roll(elevation, 1) + np.roll(elevation, -1)) / 2.0
        roughness = np.abs(elevation - neighbours)
        self.roughness: FloatArray = np.where(np.isfinite(roughness), roughness, 0.0)
        self.any_no_data = bool(np.isnan(elevation).any())
        known = elevation[np.isfinite(elevation)]
        self.max_known = float(known.max()) if known.size else math.nan

    @classmethod
    def idealized(cls) -> "HorizonModel":
        zeros = np.zeros(4)
        return cls(90.0, zeros, np.zeros(4, dtype=bool), np.full(4, np.nan), "idealized")

    @classmethod
    def from_profile(cls, profile: HorizonProfile) -> "HorizonModel":
        if profile.status == "unavailable":
            raise ValueError("profilul de orizont indisponibil nu poate defini un model")
        elevation = np.array(
            [math.nan if v is None else v for v in profile.elevation_deg], dtype=float
        )
        distance = np.array(
            [math.nan if v is None else v for v in profile.obstacle_distance_m], dtype=float
        )
        lower = np.array([q == "partial" for q in profile.quality], dtype=bool)
        return cls(profile.azimuth_step_deg, elevation, lower, distance, "dem")

    def evaluate(self, azimuth_deg: FloatArray) -> tuple[FloatArray, BoolArray, FloatArray]:
        """(H, limită inferioară, rugozitate locală) la azimuturile date; NaN unde lipsesc date."""
        position = np.mod(azimuth_deg, 360.0) / self.step_deg
        low = np.floor(position)
        fraction = position - low
        i: IntArray = low.astype(np.int64) % self.count
        j: IntArray = (i + 1) % self.count
        h = self.elevation[i] * (1.0 - fraction) + self.elevation[j] * fraction
        lower = self.lower_bound[i] | self.lower_bound[j]
        rough = np.maximum(self.roughness[i], self.roughness[j])
        return h, lower, rough

    def obstacle_distance_at(self, azimuth_deg: float) -> float | None:
        if self.kind != "dem":
            return None
        index = round((azimuth_deg % 360.0) / self.step_deg) % self.count
        value = float(self.obstacle_distance[index])
        return value if math.isfinite(value) else None


@dataclass(frozen=True)
class SunVisibility:
    state: SunState
    reason: UndeterminedReason | None
    data: DataState
    clearance_deg: float | None
    eps_deg: float
    fraction: float | None
    fraction_uncertainty: float | None
    contact_azimuth_deg: float | None

    @property
    def timeline_state(self) -> TimelineState:
        if self.state in ("partially_visible", "fully_visible"):
            return "visible"
        return "hidden" if self.state == "hidden" else "unknown"


@dataclass(frozen=True)
class EarthVisibility:
    state: EarthState
    reason: UndeterminedReason | None
    data: DataState
    margin_deg: float | None
    eps_deg: float
    horizon_deg: float | None
    cause: Cause

    @property
    def timeline_state(self) -> TimelineState:
        if self.state == "visible":
            return "visible"
        return "hidden" if self.state == "hidden" else "unknown"


def _columns(rho: float, count: int) -> FloatArray:
    columns: FloatArray = -rho + (np.arange(count, dtype=float) + 0.5) * (2.0 * rho / count)
    return columns


def _fraction(top: FloatArray, bottom: FloatArray, horizon: FloatArray) -> float:
    visible = np.clip(top - np.maximum(horizon, bottom), 0.0, None)
    total = float(np.sum(top - bottom))
    return float(np.sum(visible)) / total if total > 0 else 0.0


def sun_visibility(
    model: HorizonModel,
    azimuth_deg: float | None,
    elevation_deg: float,
    angular_radius_deg: float,
    columns: int = DISC_COLUMNS,
) -> SunVisibility:
    """Starea discului solar față de H(A) (criteriul D-04: arie pozitivă vizibilă)."""
    rho = angular_radius_deg
    cos_e = math.cos(math.radians(elevation_deg))
    if azimuth_deg is None or cos_e * 180.0 <= rho:
        # Zenit sau nadir: discul acoperă toate azimuturile; se compară cu orizontul cunoscut maxim.
        return _sun_with_undefined_azimuth(model, elevation_deg, rho)
    x = _columns(rho, columns)
    # Pentru g: și eșantioanele profilului din interiorul discului (vârfurile lui H liniar).
    half_width = rho / cos_e
    first = math.floor((azimuth_deg - half_width) / model.step_deg)
    last = math.ceil((azimuth_deg + half_width) / model.step_deg)
    breakpoints = (np.arange(first, last + 1) * model.step_deg - azimuth_deg) * cos_e
    breakpoints = breakpoints[np.abs(breakpoints) < rho]
    points = np.concatenate([x, breakpoints, [0.0]])
    azimuths = azimuth_deg + points / cos_e
    horizon, lower, rough = model.evaluate(azimuths)
    half = np.sqrt(np.maximum(rho * rho - points * points, 0.0))
    top = elevation_deg + half
    bottom = elevation_deg - half
    eps = max(EPS_NUMERIC_DEG, float(rough.max()))
    if bool(np.isnan(horizon).any()):
        return SunVisibility("undetermined", "no_data", "no_data", None, eps, None, None, None)
    margins = top - horizon
    best = int(np.argmax(margins))
    g = float(margins[best])
    h = float(np.min(bottom - horizon))
    contact = float(azimuths[best] % 360.0)
    data: DataState = "lower_bound" if bool(lower.any()) else "ok"
    if g < -eps:
        # Sigur ascuns: un orizont real mai înalt (limită inferioară) nu poate descoperi discul.
        return SunVisibility("hidden", None, data, g, eps, 0.0, 0.0, contact)
    if data == "lower_bound":
        return SunVisibility("undetermined", "partial_data", data, g, eps, None, None, contact)
    n = columns
    col_h, col_top, col_bottom = horizon[:n], top[:n], bottom[:n]
    fraction = _fraction(col_top, col_bottom, col_h)
    upper = _fraction(col_top, col_bottom, col_h - eps)
    lower_f = _fraction(col_top, col_bottom, col_h + eps)
    coarse = _fraction(col_top[1::2], col_bottom[1::2], col_h[1::2])
    uncertainty = min(max(upper - fraction, fraction - lower_f) + abs(fraction - coarse), 1.0)
    if g <= eps:
        return SunVisibility(
            "undetermined", "near_threshold", data, g, eps, fraction, uncertainty, contact
        )
    if h > eps:
        return SunVisibility("fully_visible", None, data, g, eps, 1.0, 0.0, contact)
    return SunVisibility(
        "partially_visible", None, data, g, eps, min(fraction, 1.0), uncertainty, contact
    )


def _sun_with_undefined_azimuth(
    model: HorizonModel, elevation_deg: float, rho: float
) -> SunVisibility:
    eps = max(EPS_NUMERIC_DEG, float(model.roughness.max()))
    if model.any_no_data:
        return SunVisibility("undetermined", "no_data", "no_data", None, eps, None, None, None)
    g = elevation_deg + rho - model.max_known
    if elevation_deg < 0.0:
        if g < -eps:
            return SunVisibility("hidden", None, "ok", g, eps, 0.0, 0.0, None)
        return SunVisibility("undetermined", "near_threshold", "ok", g, eps, None, None, None)
    if elevation_deg - rho - model.max_known > eps:
        return SunVisibility("fully_visible", None, "ok", g, eps, 1.0, 0.0, None)
    return SunVisibility("undetermined", "near_threshold", "ok", g, eps, None, None, None)


def earth_visibility(
    model: HorizonModel,
    azimuth_deg: float | None,
    elevation_deg: float,
    min_elevation_deg: float,
) -> EarthVisibility:
    """Vizibilitate geometrică spre centrul Pământului: e > max(H(A), e_min)."""
    if azimuth_deg is None:
        horizon_value = model.max_known
        no_data = model.any_no_data
        lower = bool(model.lower_bound.any())
        eps = max(EPS_NUMERIC_DEG, float(model.roughness.max()))
    else:
        h, low, rough = model.evaluate(np.array([azimuth_deg], dtype=float))
        horizon_value = float(h[0])
        no_data = math.isnan(horizon_value)
        lower = bool(low[0])
        eps = max(EPS_NUMERIC_DEG, float(rough[0]))
    cause: Cause
    if model.kind == "idealized":
        cause = "idealized_horizon" if min_elevation_deg <= 0.0 else "elevation_threshold"
    elif not no_data and horizon_value >= min_elevation_deg:
        cause = "terrain"
    else:
        cause = "elevation_threshold"
    if no_data:
        return EarthVisibility("undetermined", "no_data", "no_data", None, eps, None, cause)
    margin = elevation_deg - max(horizon_value, min_elevation_deg)
    data: DataState = "lower_bound" if lower else "ok"
    if margin < -eps:
        return EarthVisibility("hidden", None, data, margin, eps, horizon_value, cause)
    if lower:
        return EarthVisibility(
            "undetermined", "partial_data", data, margin, eps, horizon_value, cause
        )
    if margin <= eps:
        return EarthVisibility(
            "undetermined", "near_threshold", data, margin, eps, horizon_value, cause
        )
    return EarthVisibility("visible", None, data, margin, eps, horizon_value, cause)


def idealized_disc_fraction(elevation_deg: float, angular_radius_deg: float) -> float:
    """Fracția analitică (în plan) a discului deasupra planului local e = 0 (teste, documentare)."""
    rho = angular_radius_deg
    s = -elevation_deg  # coarda y = s, în coordonate centrate pe disc
    if s >= rho:
        return 0.0
    if s <= -rho:
        return 1.0
    area = rho * rho * math.acos(s / rho) - s * math.sqrt(rho * rho - s * s)
    return area / (math.pi * rho * rho)
