"""Profilul orizontului din DEM (docs/SPEC_FIZICA.md §6, etapa E09).

Algoritmul folosește rasterele de calcul (niciodată mesh-ul vizual):

1. pentru fiecare azimut `a_k` (pas `Δa`), distanțele `d_j` de la `d_min` la `d_max` se parcurg pe
   cercul mare care pleacă din observator (problema geodezică directă pe sfera de referință);
2. punctul se proiectează în CRS-ul fiecărui nivel (stereografic polar sud) și înălțimea se citește
   prin interpolare biliniară strictă: orice vecin fără date face eșantionul invalid;
3. nivelul apropiat are prioritate; nivelul îndepărtat se folosește numai unde cel apropiat nu are
   date (în afara rasterului sau `NoData`);
4. elevația aparentă se calculează în coordonate carteziene ME, deci curbura este inclusă:
   `el = atan2((R + h)·cos δ - r_obs, (R + h)·sin δ)`, cu `δ = d / R` și
   `r_obs = R + h_teren + h_echipament`;
5. eșantioanele fără date nu intră în maxim și nu devin zero; se numără separat.

Starea per azimut: `complete` (toate eșantioanele până la `d_max` au date), `partial` (lipsesc
unele; maximul real poate fi mai mare), `no_data` (niciun eșantion valid).

Nivelurile se combină numai dacă declară același cadru și aceeași sferă de referință; verificarea
se face aici, nu la apelant.
"""

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import numpy as np
import rasterio
from numpy.typing import NDArray

from lunarhorizon.core.coords import enu_basis

ALGORITHM_VERSION: Final = "e09.1"
AzimuthQuality = Literal["complete", "partial", "no_data"]
FloatArray = NDArray[np.float64]
# Numărul de azimuturi procesate împreună (memoria crește liniar cu el).
_AZIMUTH_CHUNK: Final = 48


class HorizonInputError(ValueError):
    """Niveluri de teren incompatibile sau parametri invalizi."""


@dataclass(frozen=True)
class HorizonParameters:
    """Parametrii tehnici ai profilului; provizorii până la D-08/D-09 [GEO]."""

    azimuth_step_deg: float
    d_min_m: float
    d_max_m: float
    near_step_m: float
    far_step_m: float

    def __post_init__(self) -> None:
        count = 360.0 / self.azimuth_step_deg if self.azimuth_step_deg > 0 else 0.0
        if self.azimuth_step_deg <= 0 or abs(count - round(count)) > 1e-9:
            raise HorizonInputError("azimuth_step_deg trebuie să dividă exact 360")
        if not 0 < self.d_min_m < self.d_max_m:
            raise HorizonInputError("trebuie 0 < d_min_m < d_max_m")
        if self.near_step_m <= 0 or self.far_step_m <= 0:
            raise HorizonInputError("pașii radiali trebuie să fie pozitivi")

    @property
    def azimuth_count(self) -> int:
        return round(360.0 / self.azimuth_step_deg)

    def as_dict(self) -> dict[str, float | str]:
        return {
            "algorithm_version": ALGORITHM_VERSION,
            "azimuth_step_deg": self.azimuth_step_deg,
            "d_min_m": self.d_min_m,
            "d_max_m": self.d_max_m,
            "near_step_m": self.near_step_m,
            "far_step_m": self.far_step_m,
        }


@dataclass(frozen=True)
class HeightGrid:
    """Raster regulat în proiecția stereografică polară sud (x spre lon 90° E, y spre lon 0°).

    `heights` poate fi un tablou de numere reale (NaN = fără date) sau întregi scalați (`scale`).
    `x_first_m` și `y_first_m` sunt coordonatele centrului pixelului (rând 0, coloană 0); rândurile
    cresc spre y descrescător.
    """

    product_id: str
    role: Literal["near", "far"]
    frame_id: str
    reference_radius_m: float
    resolution_m: float
    x_first_m: float
    y_first_m: float
    heights: NDArray[np.float32] | NDArray[np.int16]
    scale: float = 1.0
    sha256: str | None = None

    @property
    def shape(self) -> tuple[int, int]:
        rows, cols = self.heights.shape
        return int(rows), int(cols)

    def bounds_m(self) -> tuple[float, float, float, float]:
        """(x_min, y_min, x_max, y_max) ale centrelor pixelilor marginali."""
        rows, cols = self.shape
        x_last = self.x_first_m + (cols - 1) * self.resolution_m
        y_last = self.y_first_m - (rows - 1) * self.resolution_m
        return self.x_first_m, y_last, x_last, self.y_first_m

    def project(
        self, latitude_rad: FloatArray, longitude_rad: FloatArray
    ) -> tuple[FloatArray, FloatArray]:
        rho = 2.0 * self.reference_radius_m * np.tan(np.pi / 4.0 + latitude_rad / 2.0)
        return rho * np.sin(longitude_rad), rho * np.cos(longitude_rad)

    def sample(self, x_m: FloatArray, y_m: FloatArray) -> FloatArray:
        """Interpolare biliniară strictă; NaN la margine, în afara rasterului sau lângă NoData."""
        rows, cols = self.shape
        col = (x_m - self.x_first_m) / self.resolution_m
        row = (self.y_first_m - y_m) / self.resolution_m
        out = np.full(col.shape, np.nan)
        finite = np.isfinite(col) & np.isfinite(row)
        c0 = np.floor(np.where(finite, col, -1.0)).astype(np.int64)
        r0 = np.floor(np.where(finite, row, -1.0)).astype(np.int64)
        inside = finite & (c0 >= 0) & (r0 >= 0) & (c0 + 1 < cols) & (r0 + 1 < rows)
        if not inside.any():
            return out
        ci, ri = c0[inside], r0[inside]
        dx, dy = col[inside] - ci, row[inside] - ri
        grid = self.heights
        v00 = grid[ri, ci].astype(np.float64)
        v01 = grid[ri, ci + 1].astype(np.float64)
        v10 = grid[ri + 1, ci].astype(np.float64)
        v11 = grid[ri + 1, ci + 1].astype(np.float64)
        value = (
            v00 * (1 - dx) * (1 - dy) + v01 * dx * (1 - dy) + v10 * (1 - dx) * dy + v11 * dx * dy
        ) * self.scale
        # NaN se propagă: un singur vecin fără date invalidează eșantionul.
        out[inside] = value
        return out


def load_geotiff_grid(
    path: Path,
    product_id: str,
    role: Literal["near", "far"],
    frame_id: str,
    reference_radius_m: float,
    sha256: str | None,
) -> HeightGrid:
    """Rasterul de calcul GeoTIFF (float), cu NoData înlocuit prin NaN (nu prin zero)."""
    with rasterio.open(path) as dataset:
        transform = dataset.transform
        if transform.b != 0 or transform.d != 0 or abs(transform.a + transform.e) > 1e-9:
            raise HorizonInputError(
                f"{path.name}: rasterul trebuie să aibă pixeli pătrați, nerotiți"
            )
        data = dataset.read(1, masked=True)
        heights = np.ma.filled(data.astype(np.float32), np.nan)
        heights[~np.isfinite(heights)] = np.nan
        resolution = float(transform.a)
        return HeightGrid(
            product_id=product_id,
            role=role,
            frame_id=frame_id,
            reference_radius_m=reference_radius_m,
            resolution_m=resolution,
            x_first_m=float(transform.c) + resolution / 2.0,
            y_first_m=float(transform.f) - resolution / 2.0,
            heights=heights,
            sha256=sha256,
        )


@dataclass(frozen=True)
class ComputedHorizon:
    azimuth_step_deg: float
    elevation_deg: list[float | None]
    obstacle_distance_m: list[float | None]
    quality: list[AzimuthQuality]
    coverage_fraction: float
    samples_per_azimuth: int
    # Fracția eșantioanelor valide luate din fiecare produs (cheie: product_id).
    product_fractions: dict[str, float]
    compute_time_s: float


def radial_distances(params: HorizonParameters, near_limit_m: float) -> FloatArray:
    """Pas fin până la `near_limit_m` (cât poate acoperi nivelul apropiat), apoi pas grosier."""
    near_end = min(max(near_limit_m, params.d_min_m), params.d_max_m)
    near = np.arange(params.d_min_m, near_end, params.near_step_m, dtype=np.float64)
    far_start = near[-1] + params.far_step_m if near.size else params.d_min_m
    far = np.arange(far_start, params.d_max_m, params.far_step_m, dtype=np.float64)
    distances = np.concatenate([near, far, [params.d_max_m]])
    return np.unique(distances)


def check_compatible(tiers: Sequence[HeightGrid]) -> None:
    if not tiers:
        raise HorizonInputError("cel puțin un nivel de teren este necesar")
    frames = {tier.frame_id for tier in tiers}
    radii = {tier.reference_radius_m for tier in tiers}
    if len(frames) != 1:
        raise HorizonInputError(f"niveluri în cadre diferite: {sorted(frames)}; nicio conversie")
    if len(radii) != 1:
        raise HorizonInputError(f"niveluri cu sfere de referință diferite: {sorted(radii)}")


def compute_horizon(
    latitude_deg: float,
    longitude_deg: float,
    observer_terrain_elevation_m: float,
    observer_height_m: float,
    tiers: Sequence[HeightGrid],
    params: HorizonParameters,
) -> ComputedHorizon:
    """Profilul H(a) al unui observator; `tiers` în ordinea priorității (apropiat, îndepărtat)."""
    check_compatible(tiers)
    if not (math.isfinite(observer_terrain_elevation_m) and math.isfinite(observer_height_m)):
        raise HorizonInputError("altitudinea observatorului trebuie să fie cunoscută și finită")
    if observer_height_m < 0:
        raise HorizonInputError("înălțimea echipamentului nu poate fi negativă")
    started = time.perf_counter()
    radius = tiers[0].reference_radius_m
    east, north, up = (np.array(v) for v in enu_basis(latitude_deg, longitude_deg))
    observer_radius = radius + observer_terrain_elevation_m + observer_height_m

    near_limit = (
        _near_reach_m(tiers[0], latitude_deg, longitude_deg) if len(tiers) > 1 else math.inf
    )
    distances = radial_distances(params, near_limit)
    delta = distances / radius
    cos_d, sin_d = np.cos(delta), np.sin(delta)

    count = params.azimuth_count
    azimuths = np.radians(np.arange(count) * params.azimuth_step_deg)
    best = np.full(count, np.nan)
    best_distance = np.full(count, np.nan)
    valid_counts = np.zeros(count, dtype=np.int64)
    per_product = np.zeros(len(tiers), dtype=np.int64)

    for start in range(0, count, _AZIMUTH_CHUNK):
        az = azimuths[start : start + _AZIMUTH_CHUNK]
        tangent = np.cos(az)[:, None] * north + np.sin(az)[:, None] * east  # (n_a, 3)
        # u = cos δ · U + sin δ · t  (versorul punctului de pe cercul mare)
        u = cos_d[None, :, None] * up + sin_d[None, :, None] * tangent[:, None, :]
        latitude = np.arcsin(np.clip(u[..., 2], -1.0, 1.0))
        longitude = np.arctan2(u[..., 1], u[..., 0])
        heights = np.full(latitude.shape, np.nan)
        for index, tier in enumerate(tiers):
            missing = np.isnan(heights)
            if not missing.any():
                break
            x, y = tier.project(latitude[missing], longitude[missing])
            values = tier.sample(x, y)
            heights[missing] = values
            per_product[index] += int(np.isfinite(values).sum())
        radial = radius + heights
        elevation = np.arctan2(radial * cos_d - observer_radius, radial * sin_d)
        valid = np.isfinite(elevation)
        valid_counts[start : start + az.size] = valid.sum(axis=1)
        masked = np.where(valid, elevation, -np.inf)
        index_max = masked.argmax(axis=1)
        rows = np.arange(az.size)
        has_any = valid.any(axis=1)
        best[start : start + az.size] = np.where(has_any, masked[rows, index_max], np.nan)
        best_distance[start : start + az.size] = np.where(has_any, distances[index_max], np.nan)

    total = distances.size
    quality: list[AzimuthQuality] = [
        "complete" if n == total else ("no_data" if n == 0 else "partial") for n in valid_counts
    ]
    valid_total = int(valid_counts.sum())
    return ComputedHorizon(
        azimuth_step_deg=params.azimuth_step_deg,
        elevation_deg=[None if math.isnan(v) else math.degrees(float(v)) for v in best],
        obstacle_distance_m=[None if math.isnan(v) else float(v) for v in best_distance],
        quality=quality,
        coverage_fraction=valid_total / (total * count),
        samples_per_azimuth=total,
        product_fractions={
            tier.product_id: (int(n) / valid_total if valid_total else 0.0)
            for tier, n in zip(tiers, per_product, strict=True)
        },
        compute_time_s=time.perf_counter() - started,
    )


def _near_reach_m(tier: HeightGrid, latitude_deg: float, longitude_deg: float) -> float:
    """Distanța în plan (majorată față de sferă) până la cel mai depărtat colț al rasterului."""
    x, y = tier.project(np.radians(np.array([latitude_deg])), np.radians(np.array([longitude_deg])))
    x_min, y_min, x_max, y_max = tier.bounds_m()
    corners = [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]
    return max(math.hypot(cx - float(x[0]), cy - float(y[0])) for cx, cy in corners)


def interpolate_horizon(
    elevation_deg: Sequence[float | None], azimuth_step_deg: float, azimuth_deg: float
) -> float | None:
    """H(a) liniar între azimuturile eșantionate, continuu la 0°/360°; None lângă `no_data`."""
    count = len(elevation_deg)
    position = (azimuth_deg % 360.0) / azimuth_step_deg
    low = math.floor(position) % count
    high = (low + 1) % count
    a, b = elevation_deg[low], elevation_deg[high]
    if a is None or b is None:
        return None
    fraction = position - math.floor(position)
    return a + (b - a) * fraction
