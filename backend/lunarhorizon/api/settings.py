"""Configurația serviciului (docs/API.md §2.5; limitele sunt provizorii, decizia D-20)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, DEFAULT_MANIFEST_PATH
from lunarhorizon.catalog import DEFAULT_CATALOG_PATH, REPO_ROOT

DATA_DIR: Final = REPO_ROOT / "data"
LEIBNITZ_MANIFEST: Final = DATA_DIR / "manifests" / "leibnitz_terrain.json"
LEIBNITZ_RASTER: Final = DATA_DIR / "_cache" / "terrain" / "leibnitz_beta" / "calculation.tif"


@dataclass(frozen=True)
class Settings:
    catalog_path: Path = DEFAULT_CATALOG_PATH
    kernel_manifest_path: Path = DEFAULT_MANIFEST_PATH
    kernel_dir: Path = DEFAULT_KERNEL_DIR
    terrain_products_path: Path = DATA_DIR / "manifests" / "terrain_products.json"
    # Registrul produselor de teren (E08b): toate regiunile PGDA 104, achiziționate sau nu.
    terrain_index_path: Path = DATA_DIR / "manifests" / "terrain_index.json"
    # Mod cu un singur produs (teste, compatibilitate E05/E08): dacă unul dintre câmpuri este dat,
    # indexul nu se folosește; câmpul lipsă ia valoarea Leibnitz Beta.
    terrain_manifest_path: Path | None = None
    terrain_calculation_raster: Path | None = None
    # Fundalurile E05 (NASA SVS) și manifestul lor; se servesc numai fișierele listate în manifest.
    auxiliary_dir: Path = DATA_DIR / "_cache" / "e05_auxiliary"
    auxiliary_manifest_path: Path = DATA_DIR / "manifests" / "e05_auxiliary.json"
    # Limita duratei unei simulări (D-20, provizoriu): 366 de zile.
    max_interval_days: int = 366
    max_series_points: int = 20_000
    max_workers: int = 2
    # Numărul maxim de simulări terminate păstrate în memorie (cache).
    cache_size: int = 64
    # Serverul de dezvoltare Vite (frontend/); alte origini nu sunt permise implicit.
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
