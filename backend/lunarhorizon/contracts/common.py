"""Tipuri comune ale contractelor: timp, coordonate, identificatori, GeoJSON."""

from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from lunarhorizon.core.conventions import FrameId as FrameIdLiteral
from lunarhorizon.core.coords import normalize_longitude_deg
from lunarhorizon.core.utc import UTC_INPUT_PATTERN, canonical_utc


class Contract(BaseModel):
    """Bază pentru toate documentele: câmpuri necunoscute respinse, fără NaN sau infinit."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False, strict=True)


def _iso_date(value: str) -> str:
    date.fromisoformat(value)
    return value


SchemaVersion = Literal["0.7.0"]
FrameId = FrameIdLiteral

# Acceptă UTC cu `Z` sau cu offset; valoarea stocată este forma canonică UTC cu `Z`.
UtcTimestamp = Annotated[
    str, StringConstraints(pattern=UTC_INPUT_PATTERN), AfterValidator(canonical_utc)
]
IsoDate = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"), AfterValidator(_iso_date)
]

Latitude = Annotated[float, Field(ge=-90.0, le=90.0)]
# Longitudine normalizată: [-180, 180).
Longitude = Annotated[float, Field(ge=-180.0, lt=180.0)]
# Longitudine la intrare: [-180, 360), normalizată la validare în [-180, 180).
LongitudeInput = Annotated[
    float, Field(ge=-180.0, lt=360.0), AfterValidator(normalize_longitude_deg)
]
Azimuth = Annotated[float, Field(ge=0.0, lt=360.0)]
Elevation = Annotated[float, Field(ge=-90.0, le=90.0)]
NonNegative = Annotated[float, Field(ge=0.0)]
Positive = Annotated[float, Field(gt=0.0)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Md5 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
HttpUrl = Annotated[str, StringConstraints(pattern=r"^https?://\S+$")]
# Cale relativă cu `/`; niciun segment nu începe cu punct, deci fără `..` și fără căi absolute.
RelativePath = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$"),
]
NonEmptyText = Annotated[str, StringConstraints(min_length=1)]


class GeoJsonPolygon(Contract):
    """Poligon GeoJSON în coordonate lunare: poziții [longitudine_deg, latitudine_deg]."""

    type: Literal["Polygon"]
    coordinates: Annotated[
        list[
            Annotated[
                list[Annotated[list[float], Field(min_length=2, max_length=2)]], Field(min_length=4)
            ]
        ],
        Field(min_length=1),
    ]

    @field_validator("coordinates")
    @classmethod
    def _closed_rings_in_range(cls, rings: list[list[list[float]]]) -> list[list[list[float]]]:
        for ring in rings:
            if ring[0] != ring[-1]:
                raise ValueError(
                    "inelul poligonului trebuie să fie închis (prima poziție = ultima)"
                )
            for lon, lat in ring:
                if not (-180.0 <= lon < 180.0 and -90.0 <= lat <= 90.0):
                    raise ValueError(f"poziție în afara domeniului: [{lon}, {lat}]")
        return rings
