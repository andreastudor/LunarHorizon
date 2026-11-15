"""Serviciul profilului de orizont (E09): niveluri de teren, verificare și cache.

- Nivelul apropiat: produsul DEM ales pentru punct prin regula deterministă a registrului
  (`DataRegistry.select_terrain`), în cadrul cerut; altitudinea observatorului vine din el.
- Nivelul îndepărtat: produsul `role = "far"` din `terrain_products.json` cu același cadru, dacă
  fișierele lui sunt pe mașină și sumele lor corespund. Fără el profilul rămâne `partial`.
- Fiecare raster se verifică (SHA-256) o singură dată pe proces, înainte de folosire.
- Cache în memorie (LRU) și pe disc (`data/_cache/horizon/<cheie>.json`). Cheia cuprinde poziția,
  cadrul, înălțimea echipamentului, produsele cu sumele lor, parametrii și versiunea algoritmului.
  Profilurile indisponibile nu se păstrează în cache.
"""

import hashlib
import json
import logging
import math
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from lunarhorizon.api.data import DataRegistry, TerrainEntry
from lunarhorizon.contracts.horizon import (
    HorizonProductUse,
    HorizonProfile,
    HorizonUnavailableReason,
)
from lunarhorizon.contracts.manifests import DemProduct, DemProductManifest
from lunarhorizon.core.conventions import SCHEMA_VERSION
from lunarhorizon.core.coords import azimuth_convention, normalize_longitude_deg
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.terrain.horizon import (
    ComputedHorizon,
    HeightGrid,
    HorizonParameters,
    compute_horizon,
    load_geotiff_grid,
)
from lunarhorizon.terrain.lola_gdr import load_lola_polar_grid

LOGGER = logging.getLogger(__name__)

# Propunere tehnică E09 (studiul de convergență din docs/VALIDARE.md); D-08/D-09 [GEO] deschise.
DEFAULT_PARAMETERS: Final = HorizonParameters(
    azimuth_step_deg=0.5,
    d_min_m=5.0,
    d_max_m=300_000.0,
    near_step_m=5.0,
    far_step_m=120.0,
)
NOTE: Final = (
    "Horizon from the DEM calculation rasters (not the display mesh). Parameters are technical "
    "proposals pending D-08/D-09; not a scientifically validated horizon."
)
_MEMORY_ENTRIES: Final = 128
_GRID_ENTRIES: Final = 3

# Motivul indisponibilității → eroarea pentru simulări (nu se trece la modul idealizat).
UNAVAILABLE_ERRORS: Final[dict[str, ErrorCode]] = {
    "frame_mismatch": ErrorCode.UNSUPPORTED_FRAME,
    "terrain_not_downloaded": ErrorCode.TERRAIN_DATA_MISSING,
    "coverage_unverified": ErrorCode.OUT_OF_DEM_COVERAGE,
    "no_dem_coverage": ErrorCode.OUT_OF_DEM_COVERAGE,
    "observer_elevation_unknown": ErrorCode.OUT_OF_DEM_COVERAGE,
}


@dataclass(frozen=True)
class FarProduct:
    product: DemProduct
    label_path: Path
    image_path: Path
    image_sha256: str | None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


class HorizonService:
    def __init__(
        self,
        registry: DataRegistry,
        far_terrain_dir: Path,
        cache_dir: Path | None,
        parameters: HorizonParameters = DEFAULT_PARAMETERS,
    ) -> None:
        self._registry = registry
        self._far_dir = far_terrain_dir
        self._cache_dir = cache_dir
        self.parameters = parameters
        self._lock = threading.Lock()
        self._compute_lock = threading.Lock()
        self._memory: OrderedDict[str, HorizonProfile] = OrderedDict()
        self._grids: OrderedDict[str, HeightGrid] = OrderedDict()
        self._verified: dict[Path, bool] = {}

    # --- nivelurile de teren ---------------------------------------------------------------

    def _verify(self, path: Path, expected: str | None) -> bool:
        """SHA-256 al fișierului față de manifest, o dată pe proces; fără sumă: nu se folosește."""
        with self._lock:
            known = self._verified.get(path)
        if known is not None:
            return known
        ok = expected is not None and path.is_file() and _sha256(path) == expected
        if not ok:
            LOGGER.warning("suma SHA-256 nu corespunde sau lipsește: %s", path)
        with self._lock:
            self._verified[path] = ok
        return ok

    def far_product(self, frame_id: str) -> FarProduct | None:
        path = self._registry.settings.terrain_products_path
        if not path.is_file():
            return None
        manifest = DemProductManifest.model_validate_json(path.read_text(encoding="utf-8"))
        candidates = sorted(
            (p for p in manifest.products if p.role == "far" and p.frame_id == frame_id),
            key=lambda p: (p.resolution_m, p.product_id),
        )
        for product in candidates:
            files = {f.kind: f for f in product.files}
            if "height" not in files or "label" not in files:
                continue
            image = self._far_dir / files["height"].filename
            label = self._far_dir / files["label"].filename
            if image.is_file() and label.is_file():
                return FarProduct(product, label, image, files["height"].sha256)
        return None

    def _grid(self, key: str, loader: Callable[[], HeightGrid]) -> HeightGrid:
        with self._lock:
            grid = self._grids.get(key)
            if grid is not None:
                self._grids.move_to_end(key)
                return grid
        grid = loader()
        with self._lock:
            self._grids[key] = grid
            while len(self._grids) > _GRID_ENTRIES:
                self._grids.popitem(last=False)
        return grid

    def _near_grid(self, entry: TerrainEntry) -> HeightGrid | None:
        manifest = entry.manifest
        if not self._verify(entry.calculation_raster, manifest.source.sha256):
            return None
        return self._grid(
            f"near:{manifest.terrain_id}",
            lambda: load_geotiff_grid(
                entry.calculation_raster,
                manifest.source.product_id,
                "near",
                manifest.frame_id,
                manifest.reference_radius_m,
                manifest.source.sha256,
            ),
        )

    def _far_grid(self, far: FarProduct) -> HeightGrid | None:
        if not self._verify(far.image_path, far.image_sha256):
            return None
        return self._grid(
            f"far:{far.product.product_id}",
            lambda: load_lola_polar_grid(
                far.label_path, far.image_path, far.product.product_id, far.image_sha256
            ),
        )

    # --- profilul --------------------------------------------------------------------------

    def profile(
        self,
        latitude_deg: float,
        longitude_deg: float,
        frame_id: str,
        observer_height_m: float,
        parameters: HorizonParameters | None = None,
    ) -> HorizonProfile:
        params = parameters or self.parameters
        longitude_deg = normalize_longitude_deg(longitude_deg)
        selection = self._registry.select_terrain(latitude_deg, longitude_deg, frame_id)
        base = _Request(latitude_deg, longitude_deg, frame_id, observer_height_m, params)
        if selection.status != "terrain_available" or selection.entry is None:
            return base.unavailable(_reason_code(selection.status), selection.reason, [])
        near = self._near_grid(selection.entry)
        if near is None:
            return base.unavailable(
                "terrain_not_downloaded",
                f"{selection.entry.manifest.terrain_id}: calculation raster checksum mismatch",
                [],
            )
        observer = _observer_elevation(near, latitude_deg, longitude_deg)
        far_product = self.far_product(frame_id)
        far = self._far_grid(far_product) if far_product else None
        tiers = [near] if far is None else [near, far]
        if observer is None:
            return base.unavailable(
                "observer_elevation_unknown",
                "the calculation raster has no valid height at the observer (edge or NoData)",
                [_product_use(tier, 0.0) for tier in tiers],
            )
        key = base.cache_key(tiers)
        cached = self._lookup(key)
        if cached is not None:
            return cached
        # Un singur calcul la un moment dat: limitează memoria (tablourile pe blocuri de azimut).
        with self._compute_lock:
            cached = self._lookup(key)
            if cached is not None:
                return cached
            computed = compute_horizon(
                latitude_deg, longitude_deg, observer, observer_height_m, tiers, params
            )
            result = base.computed(key, observer, tiers, computed, far_missing=far is None)
            self._store(key, result)
        return result

    def _lookup(self, key: str) -> HorizonProfile | None:
        with self._lock:
            hit = self._memory.get(key)
            if hit is not None:
                self._memory.move_to_end(key)
                return hit
        if self._cache_dir is not None:
            path = self._cache_dir / f"{key}.json"
            if path.is_file():
                try:
                    profile = HorizonProfile.model_validate_json(path.read_text(encoding="utf-8"))
                except ValueError:
                    LOGGER.warning("intrare de cache invalidă ignorată: %s", path)
                    return None
                if profile.cache_key == key:
                    self._remember(key, profile)
                    return profile
        return None

    def _remember(self, key: str, profile: HorizonProfile) -> None:
        with self._lock:
            self._memory[key] = profile
            self._memory.move_to_end(key)
            while len(self._memory) > _MEMORY_ENTRIES:
                self._memory.popitem(last=False)

    def _store(self, key: str, profile: HorizonProfile) -> None:
        self._remember(key, profile)
        if self._cache_dir is None:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            target = self._cache_dir / f"{key}.json"
            partial = target.with_suffix(".json.part")
            partial.write_text(profile.model_dump_json(), encoding="utf-8")
            partial.replace(target)
        except OSError:
            LOGGER.warning("profilul nu a putut fi scris în cache: %s", key)


def require_available(profile: HorizonProfile) -> None:
    """Pentru simulări: un profil indisponibil oprește cererea (nu se trece la modul idealizat)."""
    if profile.status == "unavailable":
        code = UNAVAILABLE_ERRORS.get(profile.reason_code or "", ErrorCode.OUT_OF_DEM_COVERAGE)
        raise LunarHorizonError(
            code,
            f"terrain_mode=dem: horizon unavailable ({profile.reason_code}): {profile.reason}; "
            "the service does not switch to the idealized mode",
        )


def _reason_code(status: str) -> HorizonUnavailableReason:
    if status == "frame_mismatch":
        return "frame_mismatch"
    if status == "terrain_not_downloaded":
        return "terrain_not_downloaded"
    if status == "coverage_unverified":
        return "coverage_unverified"
    return "no_dem_coverage"


def _observer_elevation(
    grid: HeightGrid, latitude_deg: float, longitude_deg: float
) -> float | None:
    x, y = grid.project(np.radians(np.array([latitude_deg])), np.radians(np.array([longitude_deg])))
    value = float(grid.sample(x, y)[0])
    return value if math.isfinite(value) else None


def _product_use(grid: HeightGrid, fraction: float) -> HorizonProductUse:
    return HorizonProductUse.model_validate(
        {
            "product_id": grid.product_id,
            "role": grid.role,
            "frame_id": grid.frame_id,
            "resolution_m": grid.resolution_m,
            "reference_radius_m": grid.reference_radius_m,
            "sha256": grid.sha256,
            "valid_sample_fraction": fraction,
        }
    )


@dataclass(frozen=True)
class _Request:
    latitude_deg: float
    longitude_deg: float
    frame_id: str
    observer_height_m: float
    params: HorizonParameters

    def cache_key(self, tiers: list[HeightGrid]) -> str:
        document = {
            "latitude_deg": repr(self.latitude_deg),
            "longitude_deg": repr(self.longitude_deg),
            "frame_id": self.frame_id,
            "observer_height_m": repr(self.observer_height_m),
            "products": [[t.product_id, t.role, t.sha256] for t in tiers],
            "parameters": self.params.as_dict(),
        }
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _common(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "latitude_deg": self.latitude_deg,
            "longitude_deg": self.longitude_deg,
            "frame_id": self.frame_id,
            "azimuth_convention": azimuth_convention(self.latitude_deg),
            "observer_height_m": self.observer_height_m,
            "azimuth_step_deg": self.params.azimuth_step_deg,
            "max_search_distance_m": self.params.d_max_m,
            "parameters": dict(self.params.as_dict()),
            "parameters_status": "provisional",
            "note": NOTE,
        }

    def unavailable(
        self,
        code: HorizonUnavailableReason,
        reason: str,
        products: list[HorizonProductUse],
    ) -> HorizonProfile:
        return HorizonProfile.model_validate(
            {
                **self._common(),
                "status": "unavailable",
                "reason_code": code,
                "reason": reason,
                "observer_terrain_elevation_m": None,
                "elevation_deg": [],
                "obstacle_distance_m": [],
                "quality": [],
                "coverage_fraction": 0.0,
                "dem_products": products,
                "cache_key": self.cache_key([]),
                "compute_time_s": None,
            }
        )

    def computed(
        self,
        key: str,
        observer_m: float,
        tiers: list[HeightGrid],
        computed: ComputedHorizon,
        far_missing: bool,
    ) -> HorizonProfile:
        incomplete = [q for q in computed.quality if q != "complete"]
        reason = None
        if incomplete:
            no_data = sum(q == "no_data" for q in incomplete)
            reason = (
                f"{len(incomplete)} of {len(computed.quality)} azimuths lack samples up to "
                f"{self.params.d_max_m / 1000:g} km ({no_data} without any valid sample); the true "
                "horizon there may be higher"
            )
            if far_missing:
                reason += "; no far-terrain product is available on this machine"
        return HorizonProfile.model_validate(
            {
                **self._common(),
                "status": "partial" if incomplete else "complete",
                "reason_code": "missing_samples" if incomplete else None,
                "reason": reason,
                "observer_terrain_elevation_m": observer_m,
                "elevation_deg": computed.elevation_deg,
                "obstacle_distance_m": computed.obstacle_distance_m,
                "quality": computed.quality,
                "coverage_fraction": computed.coverage_fraction,
                "dem_products": [
                    _product_use(t, computed.product_fractions.get(t.product_id, 0.0))
                    for t in tiers
                ],
                "cache_key": key,
                "compute_time_s": computed.compute_time_s,
            }
        )
