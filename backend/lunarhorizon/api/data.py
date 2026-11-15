"""Datele încărcate de serviciu: catalogul, profilurile de kerneluri și produsele DEM.

Profilul de kerneluri se alege după `frame_id` din cerere. Un cadru nu se convertește în altul:
dacă un sit declară alt cadru decât cel cerut, cererea este refuzată (vezi `simulation.service`).
"""

import json
import threading
from dataclasses import dataclass
from pathlib import Path

import rasterio
import rasterio.errors

from lunarhorizon.api.settings import LEIBNITZ_MANIFEST, LEIBNITZ_RASTER, Settings
from lunarhorizon.astro.kernels import LoadedProfile, load_profile, read_manifest
from lunarhorizon.catalog import load_catalog
from lunarhorizon.contracts.catalog import Catalog
from lunarhorizon.contracts.common import GeoJsonPolygon
from lunarhorizon.contracts.manifests import DemProduct, DemProductManifest, TerrainManifest
from lunarhorizon.contracts.service import TerrainCoverage
from lunarhorizon.core.coords import CoordinateError
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.projection import SouthPolarStereographic
from lunarhorizon.terrain.sampling import sample_bilinear

EDGE_SAMPLES = 16


SOUTH_POLAR_MAX_LATITUDE_DEG = -60.0
# PGDA 81 (87-90 deg S, 5 m/pixel mosaic, 3.3 GB) is inventoried in DATA_PLAN, not acquired.
PGDA81_MAX_LATITUDE_DEG = -87.0
SOUTH_POLAR_RULE = (
    "South polar targets: catalog entries at latitude <= -60 deg. Inventory: PGDA 104 (13 regions, "
    "selective acquisition), PGDA 81 mosaic 87-90 deg S (not acquired, 3.3 GB), PGDA 78 site DEMs "
    "(codes without documented regions; not registered)."
)
SELECTION_RULE = (
    "Among the registered products whose raster rectangle contains the point and whose frame "
    "equals the requested frame: prefer a valid calculation sample (not NoData, not the raster "
    "edge), then "
    "the finer calculation resolution, then the larger distance to the raster edge, then the "
    "smaller terrain_id. Rasters are never combined."
)


@dataclass(frozen=True)
class TerrainEntry:
    manifest: TerrainManifest
    calculation_raster: Path
    product: DemProduct | None
    region_name: str

    @property
    def available(self) -> bool:
        return self.calculation_raster.is_file()


@dataclass(frozen=True)
class PendingProduct:
    """A product of the index that has not been acquired or built on this machine."""

    terrain_id: str
    product_id: str
    region_name: str
    frame_id: str
    calc_resolution_m: float
    bounds_m: tuple[float, float, float, float]  # x_min, y_min, x_max, y_max


@dataclass(frozen=True)
class TerrainSelection:
    status: str  # SiteTerrainState
    entry: TerrainEntry | None
    pending: PendingProduct | None
    reason: str


class DataRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._profiles: dict[str, LoadedProfile] = {}
        self._catalog: Catalog | None = None
        self._terrain: tuple[list[TerrainEntry], list[PendingProduct]] | None = None

    # --- catalog ---------------------------------------------------------------------------

    def catalog(self) -> Catalog:
        with self._lock:
            if self._catalog is None:
                self._catalog = load_catalog(self.settings.catalog_path)
            return self._catalog

    # --- kerneluri -------------------------------------------------------------------------

    def default_frame_id(self) -> str:
        manifest = read_manifest(self.settings.kernel_manifest_path)
        for profile in manifest.profiles:
            if profile.profile_id == manifest.default_profile:
                return profile.frame_id
        raise LunarHorizonError(ErrorCode.KERNEL_MISSING, "profilul implicit lipsește din manifest")

    def profile_for_frame(self, frame_id: str) -> LoadedProfile:
        """Profilul încărcat pentru cadrul cerut; kernelurile se verifică la prima folosire."""
        with self._lock:
            cached = self._profiles.get(frame_id)
            if cached is not None:
                return cached
            try:
                manifest = read_manifest(self.settings.kernel_manifest_path)
            except (OSError, ValueError) as error:
                raise LunarHorizonError(
                    ErrorCode.KERNEL_MISSING, "manifestul kernelurilor nu poate fi citit"
                ) from error
            for entry in manifest.profiles:
                if entry.frame_id == frame_id:
                    loaded = load_profile(
                        entry.profile_id,
                        self.settings.kernel_manifest_path,
                        self.settings.kernel_dir,
                    )
                    self._profiles[frame_id] = loaded
                    return loaded
        raise LunarHorizonError(
            ErrorCode.UNSUPPORTED_FRAME, f"niciun profil de kerneluri nu declară cadrul {frame_id}"
        )

    def loaded_profiles(self) -> list[LoadedProfile]:
        with self._lock:
            return list(self._profiles.values())

    # --- teren -----------------------------------------------------------------------------

    def terrain_entries(self) -> list[TerrainEntry]:
        """Produsele DEM construite (disponibilitatea rasterului se verifică separat)."""
        return self._terrain_state()[0]

    def pending_products(self) -> list[PendingProduct]:
        return self._terrain_state()[1]

    def _terrain_state(self) -> tuple[list[TerrainEntry], list[PendingProduct]]:
        with self._lock:
            if self._terrain is None:
                self._terrain = self._read_terrain()
            return self._terrain

    def _read_terrain(self) -> tuple[list[TerrainEntry], list[PendingProduct]]:
        settings = self.settings
        products: dict[str, DemProduct] = {}
        if settings.terrain_products_path.is_file():
            document = DemProductManifest.model_validate_json(
                settings.terrain_products_path.read_text(encoding="utf-8")
            )
            products = {product.product_id: product for product in document.products}
        if settings.terrain_manifest_path is not None or settings.terrain_calculation_raster:
            # Single-product mode (tests and E05/E08 compatibility).
            manifest_path = settings.terrain_manifest_path or LEIBNITZ_MANIFEST
            raster = settings.terrain_calculation_raster or LEIBNITZ_RASTER
            if not manifest_path.is_file():
                return [], []
            manifest = TerrainManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
            entry = TerrainEntry(
                manifest, raster, products.get(manifest.source.product_id), manifest.terrain_id
            )
            return [entry], []
        if not settings.terrain_index_path.is_file():
            return [], []
        index = json.loads(settings.terrain_index_path.read_text(encoding="utf-8"))
        root = settings.terrain_index_path.resolve().parents[2]
        entries: list[TerrainEntry] = []
        pending: list[PendingProduct] = []
        for item in index["entries"]:
            if item.get("manifest"):
                manifest = TerrainManifest.model_validate_json(
                    (root / item["manifest"]).read_text(encoding="utf-8")
                )
                if manifest.terrain_id != item["terrain_id"]:
                    raise ValueError(f"index and manifest disagree for {item['terrain_id']}")
                entries.append(
                    TerrainEntry(
                        manifest,
                        root / item["cache_dir"] / "calculation.tif",
                        products.get(manifest.source.product_id),
                        item["region_name"],
                    )
                )
            else:
                x_min, y_min, x_max, y_max = item["bounds_m"]
                pending.append(
                    PendingProduct(
                        item["terrain_id"],
                        item["product_id"],
                        item["region_name"],
                        item["frame_id"],
                        float(item["calc_resolution_m"]),
                        (x_min, y_min, x_max, y_max),
                    )
                )
        return entries, pending

    def terrain_by_id(self, terrain_id: str) -> TerrainEntry:
        for entry in self.terrain_entries():
            if entry.manifest.terrain_id == terrain_id:
                return entry
        raise LunarHorizonError(
            ErrorCode.VALIDATION_ERROR, f"terrain_id {terrain_id!r} nu este cunoscut"
        )

    def available_terrain(self) -> list[TerrainEntry]:
        return [entry for entry in self.terrain_entries() if entry.available]

    def select_terrain(
        self, latitude_deg: float, longitude_deg: float, frame_id: str | None
    ) -> TerrainSelection:
        """The terrain product for a point, by the deterministic rule `SELECTION_RULE`."""
        covering = [
            e for e in self.terrain_entries() if point_in_terrain(e, latitude_deg, longitude_deg)
        ]
        pending_covering = [
            p for p in self.pending_products() if point_in_pending(p, latitude_deg, longitude_deg)
        ]
        same_frame = [e for e in covering if frame_id is None or e.manifest.frame_id == frame_id]
        available = [e for e in same_frame if e.available]
        if available:
            ranked = sorted(
                available,
                key=lambda e: (
                    0 if sample_at(e, latitude_deg, longitude_deg) is not None else 1,
                    e.manifest.calc_resolution_m,
                    -edge_distance_m(e, latitude_deg, longitude_deg),
                    e.manifest.terrain_id,
                ),
            )
            best = ranked[0]
            return TerrainSelection(
                "terrain_available", best, None, f"{best.manifest.terrain_id} selected"
            )
        if same_frame:
            missing = same_frame[0]
            return TerrainSelection(
                "terrain_not_downloaded",
                missing,
                None,
                f"{missing.manifest.terrain_id}: calculation raster not on this machine",
            )
        pending_same = [p for p in pending_covering if frame_id is None or p.frame_id == frame_id]
        if pending_same:
            first = sorted(pending_same, key=lambda p: p.terrain_id)[0]
            return TerrainSelection(
                "terrain_not_downloaded", None, first, f"{first.product_id}: not acquired"
            )
        if covering or pending_covering:
            frames = sorted(
                {e.manifest.frame_id for e in covering} | {p.frame_id for p in pending_covering}
            )
            return TerrainSelection(
                "frame_mismatch",
                None,
                None,
                f"DEM declared in {', '.join(frames)}; requested {frame_id}; no conversion",
            )
        if latitude_deg <= PGDA81_MAX_LATITUDE_DEG:
            return TerrainSelection(
                "terrain_not_downloaded", None, None, "PGDA 81 mosaic (87-90 deg S) not acquired"
            )
        if latitude_deg <= SOUTH_POLAR_MAX_LATITUDE_DEG:
            return TerrainSelection(
                "coverage_unverified",
                None,
                None,
                "no inventoried product covers this south polar point; others not checked",
            )
        return TerrainSelection(
            "no_dem_coverage", None, None, "outside the south polar scope of the DEM inventory"
        )


def terrain_coverage(entry: TerrainEntry) -> TerrainCoverage:
    """Dreptunghiul rasterului în coordonate selenografice (nu acoperirea orizontului)."""
    bounds = entry.manifest.bounds
    projection = SouthPolarStereographic(radius_m=entry.manifest.reference_radius_m)
    corners = [
        (bounds.x_min_m, bounds.y_min_m),
        (bounds.x_max_m, bounds.y_min_m),
        (bounds.x_max_m, bounds.y_max_m),
        (bounds.x_min_m, bounds.y_max_m),
    ]
    ring: list[list[float]] = []
    for (x0, y0), (x1, y1) in zip(corners, [*corners[1:], corners[0]], strict=True):
        for step in range(EDGE_SAMPLES):
            fraction = step / EDGE_SAMPLES
            latitude, longitude = projection.inverse(
                x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction
            )
            ring.append([longitude, latitude])
    ring.append(ring[0])
    latitudes = [point[1] for point in ring]
    return TerrainCoverage(
        product_id=entry.manifest.source.product_id,
        role=entry.product.role if entry.product else "near",
        resolution_m=entry.manifest.calc_resolution_m,
        footprint=GeoJsonPolygon(type="Polygon", coordinates=[ring]),
        min_latitude_deg=min(latitudes),
        max_latitude_deg=max(latitudes),
    )


def point_in_terrain(entry: TerrainEntry, latitude_deg: float, longitude_deg: float) -> bool:
    """Punctul proiectat se află în dreptunghiul rasterului (nu implică orizont calculabil)."""
    projection = SouthPolarStereographic(radius_m=entry.manifest.reference_radius_m)
    try:
        x, y = projection.forward(latitude_deg, longitude_deg)
    except CoordinateError:
        return False
    bounds = entry.manifest.bounds
    return bounds.x_min_m <= x <= bounds.x_max_m and bounds.y_min_m <= y <= bounds.y_max_m


def _projected(radius_m: float, latitude_deg: float, longitude_deg: float) -> tuple[float, float]:
    return SouthPolarStereographic(radius_m=radius_m).forward(latitude_deg, longitude_deg)


def point_in_pending(product: PendingProduct, latitude_deg: float, longitude_deg: float) -> bool:
    try:
        x, y = _projected(1_737_400.0, latitude_deg, longitude_deg)
    except CoordinateError:
        return False
    x_min, y_min, x_max, y_max = product.bounds_m
    return x_min <= x <= x_max and y_min <= y <= y_max


def edge_distance_m(entry: TerrainEntry, latitude_deg: float, longitude_deg: float) -> float:
    x, y = _projected(entry.manifest.reference_radius_m, latitude_deg, longitude_deg)
    b = entry.manifest.bounds
    return min(x - b.x_min_m, b.x_max_m - x, y - b.y_min_m, b.y_max_m - y)


def sample_at(entry: TerrainEntry, latitude_deg: float, longitude_deg: float) -> float | None:
    """Height from the calculation raster (bilinear); None at the edge or in NoData."""
    x, y = _projected(entry.manifest.reference_radius_m, latitude_deg, longitude_deg)
    try:
        return sample_bilinear(entry.calculation_raster, x, y)
    except (OSError, rasterio.errors.RasterioError):
        return None
