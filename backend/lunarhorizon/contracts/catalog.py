"""Catalogul siturilor (docs/SPECIFICATIE.md §6, docs/API.md §2.2).

Schema 0.3.0 (E04) adaugă trasabilitatea pozițiilor: fiecare poziție are cel puțin o sursă cu
document, locator, convenții declarate și starea accesului. Validarea de aici este STRUCTURALĂ:
un catalog valid nu dovedește că poziția este corectă. Verificarea științifică este în
docs/VALIDARE.md §7 și în scripts/verify_catalog_sources.py.
"""

from typing import Literal

from pydantic import model_validator

from lunarhorizon.contracts.common import (
    Contract,
    FrameId,
    GeoJsonPolygon,
    HttpUrl,
    Identifier,
    IsoDate,
    Latitude,
    Longitude,
    NonEmptyText,
    NonNegative,
    SchemaVersion,
    Sha256,
    UtcTimestamp,
)
from lunarhorizon.core.coords import normalize_longitude_deg

# `dem_region` (schema 0.6.0): punct reprezentativ al unei regiuni documentate de un produs DEM;
# nu este loc de aterizare, țintă sau candidat. Fără misiune: `mission_status = not_applicable`.
SiteStatus = Literal["landed", "planned", "candidate", "impact", "custom", "dem_region"]
MissionStatus = Literal["landed", "impacted", "not_landed", "planned", "unknown", "not_applicable"]
GeometryType = Literal["point", "region"]
PositionKind = Literal["actual", "planned_target", "representative_point"]
SourceUse = Literal["position", "planned_target", "corroboration", "mission_context"]
SourceAccess = Literal["opened_original", "not_accessible"]
PositionVerification = Literal["verified_at_original", "incomplete", "conflict_open"]
DemoSelectionStatus = Literal["unconfirmed", "confirmed"]

# Toleranța la compararea coordonatelor adoptate cu cele originale normalizate (grade).
ADOPTION_TOLERANCE_DEG = 1e-9


class OriginalCoordinates(Contract):
    """Coordonatele exact cum apar în sursă, cu descrierea cadrului sau a convenției lor."""

    latitude_deg: Latitude
    longitude_deg: float
    frame_description: NonEmptyText
    note: str | None = None


class SourceRecord(Contract):
    """Un document sau produs consultat pentru o poziție; citarea completă este în SOURCES."""

    used_for: SourceUse
    institution: NonEmptyText
    title: NonEmptyText
    url: HttpUrl
    # Identificator de produs sau de document (DOI, ID PDS, număr de imagine), dacă există.
    identifier: str | None
    version_or_update: str | None
    # Data publicării sau actualizării, exact cum apare în sursă; `null` dacă sursa nu o oferă.
    published: str | None
    accessed_at: IsoDate
    # Pagina, tabelul, secțiunea sau înregistrarea care conține poziția.
    locator: NonEmptyText
    access: SourceAccess
    coordinates: OriginalCoordinates | None
    # Cadrul sau sistemul exact cum îl declară sursa; `null` dacă sursa nu declară nimic.
    declared_frame: str | None
    # `true` numai dacă sursa numește realizarea cadrului (de exemplu o versiune DE).
    frame_realization_stated: bool
    published_uncertainty_m: NonNegative | None
    uncertainty_definition: str | None
    # Fraza publicată care conține poziția (verificabilă pe documentul original).
    quote: str | None
    # SHA-256 al fișierului citit, când sursa este un fișier descărcat; `null` pentru pagini web.
    file_sha256: Sha256 | None

    @model_validator(mode="after")
    def _consistency(self) -> "SourceRecord":
        if self.access == "not_accessible" and (self.coordinates is not None or self.quote):
            raise ValueError("o sursă inaccesibilă nu poate oferi coordonate sau citate")
        if self.published_uncertainty_m is not None and not self.uncertainty_definition:
            raise ValueError("published_uncertainty_m cere uncertainty_definition")
        return self


class Site(Contract):
    id: Identifier
    name: NonEmptyText
    mission: str | None
    agency: str | None
    operator: str | None
    country: str | None
    # Starea intrării (poziției): o țintă planificată are `planned`, chiar dacă misiunea a aterizat.
    status: SiteStatus
    # Starea actuală a misiunii, verificată separat de starea poziției.
    mission_status: MissionStatus
    geometry_type: GeometryType
    position_kind: PositionKind
    latitude_deg: Latitude
    longitude_deg: Longitude
    frame_id: FrameId
    original_coordinates: OriginalCoordinates | None
    horizontal_uncertainty_m: NonNegative | None
    elevation_m: float | None = None
    elevation_reference: str | None = None
    region: GeoJsonPolygon | None = None
    landing_date_utc: UtcTimestamp | None = None
    # Intrarea țintă planificată trimite la poziția efectivă a aceleiași misiuni, și invers.
    related_site_id: Identifier | None
    # Ținta planificată, când sursele o dau numai ca regiune numită (fără coordonate numerice).
    planned_target_note: str | None
    source_url: HttpUrl
    accessed_at: IsoDate
    position_sources: list[SourceRecord]
    position_verification: PositionVerification
    # Alegerea valorii adoptate, normalizările aplicate și ipotezele de cadru; obligatoriu.
    adoption_note: NonEmptyText
    description_ro: str | None
    description_en: str | None
    terrain_available: bool

    def primary_source(self) -> SourceRecord:
        for source in self.position_sources:
            if source.used_for in ("position", "planned_target"):
                return source
        raise ValueError("nicio sursă de poziție")

    @model_validator(mode="after")
    def _consistency(self) -> "Site":
        if self.elevation_m is not None and not self.elevation_reference:
            raise ValueError("elevation_m cere elevation_reference")
        if self.geometry_type == "region" and self.position_kind != "representative_point":
            raise ValueError("o regiune se afișează printr-un punct etichetat representative_point")
        if self.region is not None and self.geometry_type != "region":
            raise ValueError("region este permis numai pentru geometry_type = region")
        if self.position_kind == "planned_target" and self.status != "planned":
            raise ValueError("o țintă planificată are status=planned")
        if self.position_kind == "actual" and self.status in ("planned", "candidate"):
            raise ValueError("o poziție efectivă nu poate avea status planned sau candidate")
        if self.status == "landed" and self.mission_status != "landed":
            raise ValueError("status=landed cere mission_status=landed")
        if self.status == "dem_region" and (
            self.position_kind != "representative_point"
            or self.geometry_type != "region"
            or self.mission is not None
            or self.mission_status != "not_applicable"
        ):
            raise ValueError(
                "dem_region cere punct reprezentativ de regiune, fără misiune (not_applicable)"
            )
        if self.mission_status == "not_applicable" and self.status != "dem_region":
            raise ValueError("mission_status=not_applicable este permis numai pentru dem_region")

        if not any(s.used_for in ("position", "planned_target") for s in self.position_sources):
            raise ValueError("fiecare poziție cere cel puțin o sursă de poziție")
        primary = self.primary_source()
        if self.source_url != primary.url or self.accessed_at != primary.accessed_at:
            raise ValueError("source_url și accessed_at trebuie să fie ale sursei primare")
        want_use = "planned_target" if self.position_kind == "planned_target" else "position"
        if self.position_kind != "representative_point" and primary.used_for != want_use:
            raise ValueError(f"sursa primară trebuie să aibă used_for={want_use}")

        if (
            self.horizontal_uncertainty_m is not None
            and primary.published_uncertainty_m != self.horizontal_uncertainty_m
        ):
            raise ValueError("incertitudinea trebuie să fie cea publicată de sursa primară")

        if self.position_verification == "verified_at_original":
            if primary.access != "opened_original" or primary.coordinates is None:
                raise ValueError("verificarea cere documentul original deschis, cu coordonate")
            if self.original_coordinates is None:
                raise ValueError("verificarea cere original_coordinates")
            original = primary.coordinates
            if original != self.original_coordinates:
                raise ValueError("original_coordinates trebuie să fie ale sursei primare")
            adopted_lon = normalize_longitude_deg(original.longitude_deg)
            if (
                abs(original.latitude_deg - self.latitude_deg) > ADOPTION_TOLERANCE_DEG
                or abs(adopted_lon - self.longitude_deg) > ADOPTION_TOLERANCE_DEG
            ):
                raise ValueError("coordonatele adoptate nu sunt coordonatele originale normalizate")
        return self


class DemoCandidate(Contract):
    site_id: Identifier
    advantages: list[NonEmptyText]
    limits: list[NonEmptyText]

    @model_validator(mode="after")
    def _both_sides(self) -> "DemoCandidate":
        if not self.advantages or not self.limits:
            raise ValueError("un candidat cere avantaje și limite")
        return self


class ExcludedCandidate(Contract):
    label: NonEmptyText
    reason: NonEmptyText


class DemoSiteSelection(Contract):
    """Starea deciziei D-07. Un candidat documentat NU este un sit demonstrativ aprobat."""

    decision_id: Literal["D-07"]
    status: DemoSelectionStatus
    # Goală cât timp colegii de geografie nu au ales; completată numai cu alegerea lor documentată.
    confirmed_site_ids: list[Identifier]
    candidates: list[DemoCandidate]
    excluded: list[ExcludedCandidate]
    criteria: list[NonEmptyText]

    @model_validator(mode="after")
    def _status_consistency(self) -> "DemoSiteSelection":
        candidate_ids = [c.site_id for c in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidați duplicați")
        if self.status == "unconfirmed" and self.confirmed_site_ids:
            raise ValueError("status=unconfirmed cere confirmed_site_ids goală")
        if self.status == "confirmed":
            if len(set(self.confirmed_site_ids)) < 2:
                raise ValueError("selecția confirmată cere cel puțin două situri distincte")
            if not set(self.confirmed_site_ids) <= set(candidate_ids):
                raise ValueError("situri confirmate care nu apar printre candidați")
        return self


class Catalog(Contract):
    schema_version: SchemaVersion
    catalog_version: NonEmptyText
    sites: list[Site]
    demo_site_selection: DemoSiteSelection

    @model_validator(mode="after")
    def _references(self) -> "Catalog":
        ids = [site.id for site in self.sites]
        if len(ids) != len(set(ids)):
            raise ValueError("identificatorii siturilor trebuie să fie unici")
        by_id = {site.id: site for site in self.sites}
        for site in self.sites:
            if site.related_site_id is None:
                continue
            other = by_id.get(site.related_site_id)
            if other is None:
                raise ValueError(f"{site.id}: related_site_id necunoscut {site.related_site_id!r}")
            if other.related_site_id != site.id:
                raise ValueError(f"{site.id}: legătura cu {other.id} nu este reciprocă")
            if {site.position_kind, other.position_kind} != {"planned_target", "actual"}:
                raise ValueError(
                    f"{site.id}: legătura trebuie să unească o țintă și o poziție efectivă"
                )
            if site.mission != other.mission:
                raise ValueError(f"{site.id}: intrările legate trebuie să aibă aceeași misiune")
        for candidate in self.demo_site_selection.candidates:
            if candidate.site_id not in by_id:
                raise ValueError(f"candidat necunoscut în catalog: {candidate.site_id!r}")
            if by_id[candidate.site_id].position_kind == "planned_target":
                raise ValueError("un candidat demonstrativ nu poate fi o țintă planificată")
        return self
