"""Manifestele kernelurilor și ale produselor de teren (docs/DATA_PLAN.md, docs/API.md §2.4)."""

from typing import Literal

from pydantic import Field, model_validator

from lunarhorizon.contracts.common import (
    Contract,
    Fraction,
    FrameId,
    HttpUrl,
    Identifier,
    IsoDate,
    Latitude,
    Longitude,
    Md5,
    NonEmptyText,
    NonNegativeInt,
    Positive,
    PositiveInt,
    RelativePath,
    SchemaVersion,
    Sha256,
    UtcTimestamp,
)
from lunarhorizon.core.conventions import ConventionStatus

KernelRole = Literal["spk", "binary_pck", "text_pck", "fk", "lsk"]
TerrainRole = Literal["near", "far"]
MetadataOrigin = Literal["declared_by_source", "read_from_file"]


# --- Kerneluri SPICE (data/manifests/kernels.json) ---------------------------------------------


class ChecksumReference(Contract):
    """O sumă de control așteptată, cu originea ei. Nu este suma calculată de proiect."""

    algorithm: Literal["md5", "sha256"]
    value: str
    # published_by_source: publicată de furnizor (de exemplu aa_checksums.txt de la NAIF);
    # prior_independent_download: calculată de altcineva după o descărcare anterioară.
    kind: Literal["published_by_source", "prior_independent_download"]
    source: NonEmptyText
    source_url: HttpUrl | None

    @model_validator(mode="after")
    def _value_matches_algorithm(self) -> "ChecksumReference":
        length = {"md5": 32, "sha256": 64}[self.algorithm]
        if len(self.value) != length or any(c not in "0123456789abcdef" for c in self.value):
            raise ValueError(f"valoarea {self.algorithm} trebuie să aibă {length} cifre hex mici")
        return self


class KernelFile(Contract):
    role: KernelRole
    filename: NonEmptyText
    url: HttpUrl
    # Calculate de scripts/download_kernels.py după descărcare; `null` până atunci.
    sha256: Sha256 | None
    md5: Md5 | None
    size_bytes: NonNegativeInt | None
    retrieved_at_utc: UtcTimestamp | None
    # Sume așteptate, independente de descărcarea proiectului; scriptul le verifică pe toate.
    expected_checksums: list[ChecksumReference]
    # Acoperirea fișierului pentru corpurile sau cadrul necesar profilului (SPK și PCK binar).
    coverage_start_utc: UtcTimestamp | None = None
    coverage_end_utc: UtcTimestamp | None = None


class KernelProfile(Contract):
    profile_id: Literal["de440_me421", "de421"]
    frame_id: FrameId
    # Cadrul PCK al orientării (axe principale), necesar pentru verificarea acoperirii.
    pa_frame_id: Literal["MOON_PA_DE440", "MOON_PA_DE421"]
    # „provisional” până la închiderea deciziei D-01 [ASTRO].
    status: ConventionStatus
    # Fișierele se încarcă exact în această ordine.
    files: list[KernelFile] = Field(min_length=1)
    # Intersecția acoperirilor fișierelor, calculată după descărcare.
    coverage_start_utc: UtcTimestamp | None = None
    coverage_end_utc: UtcTimestamp | None = None


class KernelManifest(Contract):
    schema_version: SchemaVersion
    default_profile: Literal["de440_me421", "de421"]
    profiles: list[KernelProfile] = Field(min_length=1)

    @model_validator(mode="after")
    def _default_exists(self) -> "KernelManifest":
        if self.default_profile not in {p.profile_id for p in self.profiles}:
            raise ValueError("default_profile trebuie să fie unul dintre profiles")
        return self


# --- Produse DEM de calcul (data/manifests/terrain_products.json) --------------------------------


class ProductFile(Contract):
    kind: Literal["height", "count", "uncertainty", "slope", "hillshade", "label", "other"]
    filename: NonEmptyText
    url: HttpUrl
    sha256: Sha256 | None
    size_bytes: NonNegativeInt | None


class DemProduct(Contract):
    product_id: Identifier
    title: NonEmptyText
    institution: NonEmptyText
    landing_page_url: HttpUrl
    citation: NonEmptyText
    accessed_at: IsoDate
    role: TerrainRole
    resolution_m: Positive
    frame_id: FrameId
    # Metadatele de mai jos sunt `null` până la citirea lor din fișier (E05); originea se declară.
    metadata_origin: MetadataOrigin
    crs_wkt: str | None
    reference_radius_m: Positive | None
    vertical_units: Literal["m"]
    vertical_reference: str | None
    nodata_value: float | None
    gap_handling: NonEmptyText
    min_latitude_deg: Latitude | None
    max_latitude_deg: Latitude | None
    files: list[ProductFile] = Field(min_length=1)


class DemProductManifest(Contract):
    schema_version: SchemaVersion
    products: list[DemProduct]


# --- Teren vizual pentru harta 3D (GET /api/terrain/manifest) ------------------------------------


class TerrainSource(Contract):
    product_id: Identifier
    url: HttpUrl
    sha256: Sha256 | None
    citation: NonEmptyText


class CrsDefinition(Contract):
    proj4: str | None
    wkt: str | None

    @model_validator(mode="after")
    def _at_least_one(self) -> "CrsDefinition":
        if not (self.proj4 or self.wkt):
            raise ValueError("CRS-ul cere cel puțin o definiție (proj4 sau wkt)")
        return self


class VerticalInfo(Contract):
    units: Literal["m"]
    reference: NonEmptyText
    # Scara verticală implicită a randării este reală (factor 1).
    exaggeration_default_factor: Literal[1]


class LocalOrigin(Contract):
    latitude_deg: Latitude
    longitude_deg: Longitude
    elevation_m: float


class ProjectedBounds(Contract):
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float

    @model_validator(mode="after")
    def _ordered(self) -> "ProjectedBounds":
        if not (self.x_min_m < self.x_max_m and self.y_min_m < self.y_max_m):
            raise ValueError("limitele trebuie să fie ordonate (min < max)")
        return self


class NoDataInfo(Contract):
    present: bool
    encoding: NonEmptyText
    # Necunoscută până la inspecția rasterului: `null`, nu 0.
    area_fraction: Fraction | None


class InterpolatedPixelsInfo(Contract):
    flagged: bool
    note: NonEmptyText


class TerrainLod(Contract):
    level: NonNegativeInt
    visual_resolution_m: Positive
    width_px: PositiveInt
    height_px: PositiveInt
    heights_path: RelativePath
    encoding: NonEmptyText
    sha256: Sha256


class TerrainManifest(Contract):
    schema_version: SchemaVersion
    terrain_id: Identifier
    source: TerrainSource
    frame_id: FrameId
    crs: CrsDefinition
    reference_radius_m: Positive
    vertical: VerticalInfo
    # Rezoluția datelor de calcul; distinctă de rezoluțiile vizuale ale nivelurilor de detaliu.
    calc_resolution_m: Positive
    local_origin: LocalOrigin
    bounds: ProjectedBounds
    nodata: NoDataInfo
    interpolated_pixels: InterpolatedPixelsInfo
    lods: list[TerrainLod] = Field(min_length=1)

    @model_validator(mode="after")
    def _lod_levels_unique(self) -> "TerrainManifest":
        levels = [lod.level for lod in self.lods]
        if len(levels) != len(set(levels)):
            raise ValueError("nivelurile de detaliu trebuie să fie unice")
        return self


class TerrainSample(Contract):
    """Altitudinea terenului într-un punct, din rasterul de calcul (/api/terrain/elevation, E08).

    Înălțimea este față de sfera de referință a produsului (`reference_radius_m` din manifest). La
    margine sau în `NoData` valoarea este `null`, cu motiv; nu se întoarce zero în locul ei.
    """

    schema_version: SchemaVersion
    terrain_id: Identifier
    product_id: Identifier
    frame_id: FrameId
    latitude_deg: Latitude
    longitude_deg: Longitude
    x_m: float
    y_m: float
    elevation_m: float | None
    reason: Literal["edge_or_nodata"] | None
    calc_resolution_m: Positive
    method: Literal["bilinear"]

    @model_validator(mode="after")
    def _unknown_has_reason(self) -> "TerrainSample":
        if (self.elevation_m is None) != (self.reason is not None):
            raise ValueError("elevation_m este null dacă și numai dacă reason este prezent")
        return self
