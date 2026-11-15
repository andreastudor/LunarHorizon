"""Production entry point: one process serves the built UI and the API together."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from lunarhorizon.api.app import create_app
from lunarhorizon.api.settings import Settings
from lunarhorizon.catalog import REPO_ROOT


def production_origins(value: str) -> tuple[str, ...]:
    origins = tuple(part.strip().rstrip("/") for part in value.split(",") if part.strip())
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ValueError("LUNAR_ALLOWED_ORIGINS must contain comma-separated HTTP origins")
    return origins


def create_production_app(frontend_dir: Path | None = None) -> FastAPI:
    origins = production_origins(os.environ.get("LUNAR_ALLOWED_ORIGINS", ""))
    app = create_app(Settings(allowed_origins=origins))
    # Mount last so /api routes retain their own handlers. Serve only the built frontend.
    folder = frontend_dir or REPO_ROOT / "frontend/dist"
    if not (folder / "index.html").is_file():
        raise RuntimeError("Frontend build missing: run npm --prefix frontend run build")
    app.mount("/", StaticFiles(directory=folder, html=True), name="frontend")
    return app
