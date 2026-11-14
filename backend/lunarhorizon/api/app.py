"""Aplicația FastAPI: `health`, `sites`, `coverage`, `terrain/manifest`, `simulations`.

Contractul endpointurilor: docs/API.md §2.

Pornire (din `backend/`): `.venv\\Scripts\\python -m uvicorn lunarhorizon.api.app:app --port 8000`.
Schema OpenAPI este la `/api/openapi.json` și se generează din aceleași modele ca JSON Schema.
E06 calculează numai modul `idealized_local_plane` (fără efectele terenului local).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lunarhorizon import __version__
from lunarhorizon.api.data import DataRegistry, point_in_terrain, terrain_coverage
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
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.contracts.service import Coverage, Health, Problem, TemporalCoverage
from lunarhorizon.contracts.simulation import (
    SimulationAccepted,
    SimulationRequest,
    SimulationStatus,
)
from lunarhorizon.core.conventions import SCHEMA_VERSION
from lunarhorizon.core.coords import normalize_longitude_deg
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import format_utc

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
                dem_products=[entry.product.product_id for entry in entries],
                time_utc=format_utc(datetime.now(tz=UTC)),
                issues=issues,
            )
        )

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

    @app.get("/api/terrain/manifest", response_model=TerrainManifest, responses=PROBLEM_RESPONSES)
    def terrain_manifest(
        site_id: Annotated[str | None, Query(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")] = None,
        latitude_deg: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
        longitude_deg: Annotated[float | None, Query(ge=-180.0, lt=360.0)] = None,
    ) -> Response:
        by_point = latitude_deg is not None or longitude_deg is not None
        if (site_id is not None) == by_point or (
            by_point and None in (latitude_deg, longitude_deg)
        ):
            raise LunarHorizonError(
                ErrorCode.VALIDATION_ERROR,
                "indicați fie site_id, fie perechea latitude_deg și longitude_deg",
            )
        if site_id is not None:
            matches = [site for site in registry.catalog().sites if site.id == site_id]
            if not matches:
                raise LunarHorizonError(
                    ErrorCode.VALIDATION_ERROR, f"site_id {site_id!r} nu există în catalog"
                )
            latitude, longitude = matches[0].latitude_deg, matches[0].longitude_deg
        else:
            assert latitude_deg is not None and longitude_deg is not None
            latitude, longitude = latitude_deg, normalize_longitude_deg(longitude_deg)
        entries = registry.terrain_entries()
        for entry in entries:
            if point_in_terrain(entry, latitude, longitude):
                if not entry.available:
                    raise LunarHorizonError(
                        ErrorCode.TERRAIN_DATA_MISSING,
                        "rasterul de calcul lipsește de pe disc; rulați "
                        "scripts/download_terrain.py "
                        "și scripts/build_terrain.py",
                    )
                return _json(entry.manifest)
        problem = make_problem(
            ErrorCode.OUT_OF_DEM_COVERAGE,
            "punctul nu se află în dreptunghiul niciunui raster DEM disponibil",
            status=404,
        )
        return _problem_response(problem)

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
