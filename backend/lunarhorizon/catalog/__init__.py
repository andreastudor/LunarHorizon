"""Cititorul catalogului siturilor (data/catalog/sites.json).

Cititorul validează documentul față de schema Pydantic și oferă căutarea după identificator.
Validarea este structurală; verificarea pozițiilor față de surse este în
scripts/verify_catalog_sources.py și în docs/VALIDARE.md §7. Endpointul `/api/sites` se
implementează la E06 peste acest cititor.
"""

from pathlib import Path
from typing import Final

from lunarhorizon.contracts.catalog import Catalog, Site

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG_PATH: Final = REPO_ROOT / "data" / "catalog" / "sites.json"


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> Catalog:
    """Citește și validează catalogul; ridică `pydantic.ValidationError` la orice abatere."""
    return Catalog.model_validate_json(path.read_text(encoding="utf-8"))


def get_site(catalog: Catalog, site_id: str) -> Site:
    for site in catalog.sites:
        if site.id == site_id:
            return site
    raise KeyError(site_id)


def planned_target_of(catalog: Catalog, site: Site) -> Site | None:
    """Ținta planificată legată de o poziție efectivă (sau invers); `None` dacă nu există."""
    return None if site.related_site_id is None else get_site(catalog, site.related_site_id)
