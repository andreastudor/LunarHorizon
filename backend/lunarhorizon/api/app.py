"""Aplicația FastAPI: `health`, `sites`, `coverage`, `terrain/manifest`, `simulations`.

Contractul endpointurilor: docs/API.md §2.

Pornire (din `backend/`): `.venv\\Scripts\\python -m uvicorn lunarhorizon.api.app:app --port 8000`.
Schema OpenAPI este la `/api/openapi.json` și se generează din aceleași modele ca JSON Schema.
E06 calculează numai modul `idealized_local_plane` (fără efectele terenului local).
"""

import hashlib
import json
import logging
import math
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

import numpy as np
import rasterio
from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from lunarhorizon import __version__
from lunarhorizon.api.data import (
    SELECTION_RULE,
    SOUTH_POLAR_RULE,
    DataRegistry,
    TerrainSelection,
    point_in_terrain,
    terrain_coverage,
)
from lunarhorizon.api.jobs import SimulationService
from lunarhorizon.api.problems import (
    PROBLEM_MEDIA_TYPE,
    from_error,
    from_validation_errors,
    internal_problem,
    make_problem,
)
from lunarhorizon.api.settings import Settings
from lunarhorizon.contracts.catalog import Catalog
from lunarhorizon.contracts.common import FrameId
from lunarhorizon.contracts.manifests import ProjectedBounds, TerrainManifest, TerrainSample
from lunarhorizon.contracts.service import (
    Coverage,
    Health,
    Problem,
    SiteTerrainStatus,
    TemporalCoverage,
    TerrainProductStatus,
    TerrainStatusReport,
)
from lunarhorizon.contracts.simulation import (
    SimulationAccepted,
    SimulationRequest,
    SimulationStatus,
)
from lunarhorizon.core.conventions import SCHEMA_VERSION
from lunarhorizon.core.coords import normalize_longitude_deg
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.projection import SouthPolarStereographic
from lunarhorizon.core.utc import format_utc
from lunarhorizon.terrain.sampling import sample_bilinear

LOGGER = logging.getLogger(__name__)

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": Problem, "content": {PROBLEM_MEDIA_TYPE: {}}}
    for status in (404, 422, 500, 503)
}


def _json(model: BaseModel, status_code: int = 200) -> Response:
    return Response(
        content=model.model_dump_json(), media_type="application/json", status_code=status_code
    )


def _problem_response(problem: Problem) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=problem.status or 500,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    registry = DataRegistry(config)
    service = SimulationService(config, registry)
    startup_issues: list[str] = []

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            registry.profile_for_frame(registry.default_frame_id())
        except LunarHorizonError as error:
            startup_issues.append(f"{error.code}: {error.detail}")
            LOGGER.warning("kernelurile nu au putut fi încărcate la pornire: %s", error.detail)
        yield
        service.shutdown()

    app = FastAPI(
        title="LunarHorizon API",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, error: RequestValidationError) -> JSONResponse:
        return _problem_response(from_validation_errors(list(error.errors())))

    @app.exception_handler(LunarHorizonError)
    async def _domain(_: Request, error: LunarHorizonError) -> JSONResponse:
        return _problem_response(from_error(error))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, error: Exception) -> JSONResponse:
        LOGGER.error("eroare neașteptată", exc_info=error)
        return _problem_response(internal_problem())

    @app.get("/api/health", response_model=Health)
    def health() -> Response:
        profiles = registry.loaded_profiles()
        issues = [] if profiles else (startup_issues or ["kernelurile nu sunt încărcate"])
        entries = registry.available_terrain()
        return _json(
            Health(
                status="ok" if profiles else "degraded",
                app_version=__version__,
                kernel_profile=profiles[0].profile_id if profiles else None,
                kernels_loaded=bool(profiles),
                dem_products=[entry.manifest.source.product_id for entry in entries],
                time_utc=format_utc(datetime.now(tz=UTC)),
                issues=issues,
            )
        )

    verified_assets: dict[str, str] = {}

    @app.get(
        "/api/assets/{name}",
        response_class=FileResponse,
        responses={200: {"content": {"image/jpeg": {}}}, **PROBLEM_RESPONSES},
    )
    def asset(name: str) -> Response:
        """Fundal E05 (NASA SVS) servit din cache, numai dacă SHA-256 corespunde manifestului."""
        try:
            manifest = json.loads(config.auxiliary_manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise LunarHorizonError(
                ErrorCode.TERRAIN_DATA_MISSING, "manifestul fundalurilor nu poate fi citit"
            ) from error
        expected = {entry["name"]: entry["sha256"] for entry in manifest.get("files", [])}
        if name not in expected or not name.endswith(".jpg"):
            raise LunarHorizonError(ErrorCode.VALIDATION_ERROR, f"resursa {name!r} nu este servită")
        path = config.auxiliary_dir / name
        if not path.is_file():
            raise LunarHorizonError(
                ErrorCode.TERRAIN_DATA_MISSING,
                f"{name} lipsește; rulați scripts/download_e05_auxiliary.py și "
                "scripts/build_e05_auxiliary.py",
            )
        if verified_assets.get(name) != expected[name]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected[name]:
                raise LunarHorizonError(
                    ErrorCode.TERRAIN_DATA_MISSING, f"{name}: SHA-256 diferă de manifest"
                )
            verified_assets[name] = digest
        return FileResponse(path, media_type="image/jpeg")

    @app.get("/api/sites", response_model=Catalog)
    def sites() -> Response:
        return _json(registry.catalog())

    @app.get("/api/coverage", response_model=Coverage, responses=PROBLEM_RESPONSES)
    def coverage(frame_id: Annotated[str | None, Query()] = None) -> Response:
        profile = registry.profile_for_frame(frame_id or registry.default_frame_id())
        return _json(
            Coverage(
                schema_version=SCHEMA_VERSION,
                temporal=TemporalCoverage(
                    start_utc=profile.coverage_start_utc,
                    end_utc=profile.coverage_end_utc,
                    kernel_profile=profile.profile_id,
                ),
                terrain=[terrain_coverage(entry) for entry in registry.available_terrain()],
            )
        )

    verified_lods: dict[str, str] = {}
    identifier = r"^[a-z0-9][a-z0-9_.-]{0,63}$"

    @app.get("/api/terrain/elevation", response_model=TerrainSample, responses=PROBLEM_RESPONSES)
    def terrain_elevation(
        terrain_id: Annotated[str, Query(pattern=identifier)],
        latitude_deg: Annotated[float, Query(ge=-90.0, le=90.0)],
        longitude_deg: Annotated[float, Query(ge=-180.0, lt=360.0)],
    ) -> Response:
        """Altitudinea terenului din rasterul de calcul (bilinear), pentru observatorul scenei."""
        entry = registry.terrain_by_id(terrain_id)
        if not entry.available:
            raise LunarHorizonError(
                ErrorCode.TERRAIN_DATA_MISSING,
                "rasterul de calcul lipsește; rulați scripts/build_terrain.py",
            )
        longitude = normalize_longitude_deg(longitude_deg)
        if not point_in_terrain(entry, latitude_deg, longitude):
            return _problem_response(
                make_problem(
                    ErrorCode.OUT_OF_DEM_COVERAGE,
                    "punctul nu se află în dreptunghiul rasterului",
                    status=404,
                )
            )
        manifest = entry.manifest
        x, y = SouthPolarStereographic(radius_m=manifest.reference_radius_m).forward(
            latitude_deg, longitude
        )
        value = sample_bilinear(entry.calculation_raster, x, y)
        return _json(
            TerrainSample(
                schema_version=SCHEMA_VERSION,
                terrain_id=manifest.terrain_id,
                product_id=manifest.source.product_id,
                frame_id=manifest.frame_id,
                latitude_deg=latitude_deg,
                longitude_deg=longitude,
                x_m=x,
                y_m=y,
                elevation_m=value,
                reason=None if value is not None else "edge_or_nodata",
                calc_resolution_m=manifest.calc_resolution_m,
                method="bilinear",
            )
        )

    @app.get(
        "/api/terrain/{terrain_id}/lods/{level}",
        response_class=Response,
        responses={200: {"content": {"application/octet-stream": {}}}, **PROBLEM_RESPONSES},
    )
    def terrain_lod(terrain_id: str, level: int) -> Response:
        """Înălțimile unui nivel de detaliu vizual: float32 little-endian, rânduri nord → sud,
        coloane vest → est, NaN = NoData. Numai fișierele listate în manifest, verificate."""
        if not re.fullmatch(identifier, terrain_id):
            raise LunarHorizonError(ErrorCode.VALIDATION_ERROR, "terrain_id invalid")
        entry = registry.terrain_by_id(terrain_id)
        lod = next((item for item in entry.manifest.lods if item.level == level), None)
        if lod is None:
            raise LunarHorizonError(
                ErrorCode.VALIDATION_ERROR, f"nivelul {level} nu există pentru {terrain_id}"
            )
        base = entry.calculation_raster.parent.resolve()
        path = (base / lod.heights_path).resolve()
        if not path.is_relative_to(base):
            raise LunarHorizonError(ErrorCode.VALIDATION_ERROR, "calea nivelului este invalidă")
        if not path.is_file():
            raise LunarHorizonError(
                ErrorCode.TERRAIN_DATA_MISSING,
                f"{lod.heights_path} lipsește; rulați scripts/build_terrain.py",
            )
        if verified_lods.get(str(path)) != lod.sha256:
            if hashlib.sha256(path.read_bytes()).hexdigest() != lod.sha256:
                raise LunarHorizonError(
                    ErrorCode.TERRAIN_DATA_MISSING,
                    f"{lod.heights_path}: SHA-256 diferă de manifest",
                )
            verified_lods[str(path)] = lod.sha256
        bounds = entry.manifest.bounds
        with rasterio.open(path) as ds:
            expected = (
                lod.visual_resolution_m,
                0.0,
                bounds.x_min_m,
                0.0,
                -lod.visual_resolution_m,
                bounds.y_max_m,
            )
            actual = tuple(ds.transform)[:6]
            if (ds.width, ds.height) != (lod.width_px, lod.height_px) or any(
                not math.isclose(a, b, abs_tol=1e-6) for a, b in zip(actual, expected, strict=True)
            ):
                raise LunarHorizonError(
                    ErrorCode.TERRAIN_DATA_MISSING,
                    f"{lod.heights_path}: dimensiunile sau georeferențierea diferă de manifest",
                )
            data = ds.read(1, masked=True)
        heights = np.ma.filled(data.astype(np.float32), np.nan)
        heights[~np.isfinite(heights)] = np.nan
        return Response(
            content=heights.astype("<f4").tobytes(),
            media_type="application/octet-stream",
            headers={
                "X-Width": str(lod.width_px),
                "X-Height": str(lod.height_px),
                "X-Lod-Level": str(lod.level),
            },
        )

    def selection_problem(selection: TerrainSelection) -> JSONResponse:
        """Problem for a point without loadable terrain (the status keeps its own code)."""
        if selection.status == "terrain_not_downloaded":
            return _problem_response(
                make_problem(
                    ErrorCode.TERRAIN_DATA_MISSING,
                    f"terrain not downloaded: {selection.reason}; run scripts/acquire_pgda104.py "
                    "and scripts/build_pgda104_regions.py",
                )
            )
        if selection.status == "frame_mismatch":
            return _problem_response(make_problem(ErrorCode.UNSUPPORTED_FRAME, selection.reason))
        return _problem_response(
            make_problem(
                ErrorCode.OUT_OF_DEM_COVERAGE,
                f"{selection.status}: {selection.reason}",
                status=404,
            )
        )

    @app.get("/api/terrain/status", response_model=TerrainStatusReport, responses=PROBLEM_RESPONSES)
    def terrain_status() -> Response:
        """Visual terrain availability per product and per catalog site (not horizon coverage)."""
        products = [
            TerrainProductStatus(
                terrain_id=entry.manifest.terrain_id,
                product_id=entry.manifest.source.product_id,
                region_name=entry.region_name,
                frame_id=entry.manifest.frame_id,
                calc_resolution_m=entry.manifest.calc_resolution_m,
                bounds=entry.manifest.bounds,
                status="available" if entry.available else "not_downloaded",
                reason=(
                    "calculation raster and visual levels on disk"
                    if entry.available
                    else "manifest versioned; raster not on this machine"
                ),
            )
            for entry in registry.terrain_entries()
        ] + [
            TerrainProductStatus(
                terrain_id=pending.terrain_id,
                product_id=pending.product_id,
                region_name=pending.region_name,
                frame_id=pending.frame_id,  # type: ignore[arg-type]
                calc_resolution_m=pending.calc_resolution_m,
                bounds=ProjectedBounds(
                    x_min_m=pending.bounds_m[0],
                    y_min_m=pending.bounds_m[1],
                    x_max_m=pending.bounds_m[2],
                    y_max_m=pending.bounds_m[3],
                ),
                status="not_downloaded",
                reason="listed in the index; not acquired",
            )
            for pending in registry.pending_products()
        ]
        sites = []
        for site in registry.catalog().sites:
            selection = registry.select_terrain(
                site.latitude_deg, site.longitude_deg, site.frame_id
            )
            sites.append(
                SiteTerrainStatus(
                    site_id=site.id,
                    status=selection.status,  # type: ignore[arg-type]
                    terrain_id=(
                        selection.entry.manifest.terrain_id
                        if selection.entry
                        else selection.pending.terrain_id
                        if selection.pending
                        else None
                    ),
                    reason=selection.reason,
                )
            )
        return _json(
            TerrainStatusReport(
                schema_version=SCHEMA_VERSION,
                south_polar_rule=SOUTH_POLAR_RULE,
                selection_rule=SELECTION_RULE,
                products=products,
                sites=sites,
            )
        )

    @app.get("/api/terrain/manifest", response_model=TerrainManifest, responses=PROBLEM_RESPONSES)
    def terrain_manifest(
        site_id: Annotated[str | None, Query(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")] = None,
        terrain_id: Annotated[str | None, Query(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")] = None,
        latitude_deg: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
        longitude_deg: Annotated[float | None, Query(ge=-180.0, lt=360.0)] = None,
        frame_id: Annotated[FrameId | None, Query()] = None,
    ) -> Response:
        """Manifest of the product selected for a site or a point (deterministic rule), or by id.

        A point is selected only among products declared in `frame_id` (the site's frame for
        `site_id`); coordinates are never converted between frames."""
        by_point = latitude_deg is not None or longitude_deg is not None
        chosen = [site_id is not None, terrain_id is not None, by_point]
        if sum(chosen) != 1 or (by_point and None in (latitude_deg, longitude_deg)):
            raise LunarHorizonError(
                ErrorCode.VALIDATION_ERROR,
                "indicați exact unul: site_id, terrain_id sau latitude_deg + longitude_deg",
            )
        if terrain_id is not None:
            entry = registry.terrain_by_id(terrain_id)
            if not entry.available:
                raise LunarHorizonError(
                    ErrorCode.TERRAIN_DATA_MISSING, f"{terrain_id}: raster not on this machine"
                )
            return _json(entry.manifest)
        if site_id is not None:
            matches = [site for site in registry.catalog().sites if site.id == site_id]
            if not matches:
                raise LunarHorizonError(
                    ErrorCode.VALIDATION_ERROR, f"site_id {site_id!r} nu există în catalog"
                )
            latitude, longitude = matches[0].latitude_deg, matches[0].longitude_deg
            frame: str | None = frame_id or matches[0].frame_id
        else:
            assert latitude_deg is not None and longitude_deg is not None
            latitude, longitude = latitude_deg, normalize_longitude_deg(longitude_deg)
            frame = frame_id
        selection = registry.select_terrain(latitude, longitude, frame)
        if selection.status == "terrain_available" and selection.entry is not None:
            return _json(selection.entry.manifest)
        return selection_problem(selection)

    @app.post(
        "/api/simulations",
        response_model=SimulationAccepted,
        status_code=202,
        responses={200: {"model": SimulationAccepted}, **PROBLEM_RESPONSES},
    )
    def create_simulation(request: SimulationRequest) -> Response:
        accepted = service.submit(request)
        return _json(accepted, 200 if accepted.cache_hit else 202)

    @app.get(
        "/api/simulations/{simulation_id}",
        response_model=SimulationStatus,
        responses=PROBLEM_RESPONSES,
    )
    def get_simulation(simulation_id: str) -> Response:
        return _json(service.status(simulation_id))

    return app


app = create_app()
