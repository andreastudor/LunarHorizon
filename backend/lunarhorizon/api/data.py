"""Datele încărcate de serviciu: catalogul, profilurile de kerneluri și produsele DEM.

Profilul de kerneluri se alege după `frame_id` din cerere. Un cadru nu se convertește în altul:
dacă un sit declară alt cadru decât cel cerut, cererea este refuzată (vezi `simulation.service`).
"""

import threading
from dataclasses import dataclass
from pathlib import Path

from lunarhorizon.api.settings import Settings
from lunarhorizon.astro.kernels import LoadedProfile, load_profile, read_manifest
from lunarhorizon.catalog import load_catalog
from lunarhorizon.contracts.catalog import Catalog
from lunarhorizon.contracts.common import GeoJsonPolygon
from lunarhorizon.contracts.manifests import DemProduct, DemProductManifest, TerrainManifest
from lunarhorizon.contracts.service import TerrainCoverage
from lunarhorizon.core.coords import CoordinateError
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.projection import SouthPolarStereographic

EDGE_SAMPLES = 16


@dataclass(frozen=True)
class TerrainEntry:
    product: DemProduct
    manifest: TerrainManifest
    calculation_raster: Path

    @property
    def available(self) -> bool:
        return self.calculation_raster.is_file()


class DataRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._profiles: dict[str, LoadedProfile] = {}
        self._catalog: Catalog | None = None
        self._terrain: list[TerrainEntry] | None = None

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
        """Produsele DEM descrise de manifeste (disponibilitatea rasterului se verifică separat)."""
        with self._lock:
            if self._terrain is None:
                self._terrain = self._read_terrain()
            return self._terrain

    def _read_terrain(self) -> list[TerrainEntry]:
        paths = (self.settings.terrain_products_path, self.settings.terrain_manifest_path)
        if not all(path.is_file() for path in paths):
            return []
        products = DemProductManifest.model_validate_json(paths[0].read_text(encoding="utf-8"))
        manifest = TerrainManifest.model_validate_json(paths[1].read_text(encoding="utf-8"))
        return [
            TerrainEntry(product, manifest, self.settings.terrain_calculation_raster)
            for product in products.products
            if product.product_id == manifest.source.product_id
        ]

    def terrain_by_id(self, terrain_id: str) -> TerrainEntry:
        for entry in self.terrain_entries():
            if entry.manifest.terrain_id == terrain_id:
                return entry
        raise LunarHorizonError(
            ErrorCode.VALIDATION_ERROR, f"terrain_id {terrain_id!r} nu este cunoscut"
        )

    def available_terrain(self) -> list[TerrainEntry]:
        return [entry for entry in self.terrain_entries() if entry.available]


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
        product_id=entry.product.product_id,
        role=entry.product.role,
        resolution_m=entry.product.resolution_m,
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
