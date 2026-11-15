"""Validarea semantică a cererii și rezolvarea siturilor (peste validarea structurală Pydantic).

Nicio regulă de aici nu schimbă modul cerut: `terrain_mode = dem` nu este înlocuit niciodată cu
modul idealizat, iar un sit din catalog cu alt cadru decât cel cerut este refuzat, nu convertit
(o schimbare de etichetă nu este o transformare de cadru).
"""

from lunarhorizon.contracts.catalog import Catalog
from lunarhorizon.contracts.simulation import (
    CatalogSiteSelection,
    CustomSiteSelection,
    SimulationRequest,
)
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import parse_utc
from lunarhorizon.simulation.idealized import SiteInput, default_series_step_s

MAX_SITES = 4


def prepare_request(
    request: SimulationRequest,
    catalog: Catalog,
    max_interval_days: int,
    max_series_points: int,
) -> tuple[SimulationRequest, list[SiteInput]]:
    """Cererea cu valorile efectiv folosite (pasul seriei) și siturile rezolvate."""
    if len(request.sites) > MAX_SITES:
        raise LunarHorizonError(ErrorCode.TOO_MANY_SITES, f"cel mult {MAX_SITES} situri")
    duration_s = (parse_utc(request.end_utc) - parse_utc(request.start_utc)).total_seconds()
    if duration_s > max_interval_days * 86_400:
        raise LunarHorizonError(
            ErrorCode.INTERVAL_TOO_LONG,
            f"durata depășește limita de {max_interval_days} de zile (D-20, provizoriu)",
        )
    # terrain_mode=dem (E09): profilul de orizont al fiecărui sit se calculează la trimitere
    # (api/jobs.py); un profil indisponibil oprește cererea, fără trecere la modul idealizat.
    step = request.series_step_s or default_series_step_s(duration_s)
    if duration_s / step + 1 > max_series_points:
        raise LunarHorizonError(
            ErrorCode.VALIDATION_ERROR,
            f"series_step_s={step} produce peste {max_series_points} de puncte; măriți pasul",
        )

    sites: list[SiteInput] = []
    seen: set[str] = set()
    for index, selection in enumerate(request.sites):
        if isinstance(selection, CatalogSiteSelection):
            site = _catalog_site(catalog, selection.site_id, request.frame_id, index)
        else:
            site = _custom_site(selection, index)
        if site.site_ref in seen:
            raise LunarHorizonError(
                ErrorCode.VALIDATION_ERROR, f"sites[{index}]: sit repetat ({site.site_ref})"
            )
        seen.add(site.site_ref)
        sites.append(site)
    return request.model_copy(update={"series_step_s": step}), sites


def _catalog_site(catalog: Catalog, site_id: str, frame_id: str, index: int) -> SiteInput:
    for site in catalog.sites:
        if site.id != site_id:
            continue
        if site.frame_id != frame_id:
            raise LunarHorizonError(
                ErrorCode.UNSUPPORTED_FRAME,
                f"sites[{index}]: {site_id} este declarat în {site.frame_id}, iar cererea "
                f"folosește {frame_id}; nu se aplică nicio transformare de cadru",
            )
        return SiteInput(
            site_ref=site.id,
            label=site.name,
            kind="catalog",
            catalog_id=site.id,
            latitude_deg=site.latitude_deg,
            longitude_deg=site.longitude_deg,
        )
    raise LunarHorizonError(
        ErrorCode.VALIDATION_ERROR, f"sites[{index}]: site_id {site_id!r} nu există în catalog"
    )


def _custom_site(selection: CustomSiteSelection, index: int) -> SiteInput:
    point = selection.custom
    return SiteInput(
        site_ref=f"custom-{index + 1}",
        label=point.label,
        kind="custom",
        catalog_id=None,
        latitude_deg=point.latitude_deg,
        longitude_deg=point.longitude_deg,
    )
