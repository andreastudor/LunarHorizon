"""Configurația serviciului (docs/API.md §2.5; limitele sunt provizorii, decizia D-20)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, DEFAULT_MANIFEST_PATH
from lunarhorizon.catalog import DEFAULT_CATALOG_PATH, REPO_ROOT

DATA_DIR: Final = REPO_ROOT / "data"


@dataclass(frozen=True)
class Settings:
    catalog_path: Path = DEFAULT_CATALOG_PATH
    kernel_manifest_path: Path = DEFAULT_MANIFEST_PATH
    kernel_dir: Path = DEFAULT_KERNEL_DIR
    terrain_products_path: Path = DATA_DIR / "manifests" / "terrain_products.json"
    terrain_manifest_path: Path = DATA_DIR / "manifests" / "leibnitz_terrain.json"
    # Rasterul de calcul local; lipsa lui înseamnă că produsul DEM nu este disponibil pe acest disc.
    terrain_calculation_raster: Path = (
        DATA_DIR / "_cache" / "terrain" / "leibnitz_beta" / "calculation.tif"
    )
    # Limita duratei unei simulări (D-20, provizoriu): 366 de zile.
    max_interval_days: int = 366
    max_series_points: int = 20_000
    max_workers: int = 2
    # Numărul maxim de simulări terminate păstrate în memorie (cache).
    cache_size: int = 64
    # Serverul de dezvoltare Vite (frontend/); alte origini nu sunt permise implicit.
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
