"""Cereri JPL Horizons pentru cazurile de referință și interpretarea răspunsurilor originale.

Horizons se folosește numai pentru verificare (docs/VALIDARE.md §3); motorul aplicației folosește
kernelurile locale. Răspunsurile se arhivează nemodificate de scripts/query_horizons.py.

Configurația: observator pe Lună (`CENTER='coord@301'`, `COORD_TYPE='GEODETIC'`), cu
`SITE_COORD = longitudine estică (grade), latitudine (grade), altitudine (km)`, unde altitudinea
include înălțimea observatorului.
"""

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Final, Literal

from lunarhorizon.astro.bodies import Body, ObserverSite

API_URL: Final = "https://ssd.jpl.nasa.gov/api/horizons.api"
BODY_COMMANDS: Final[dict[Body, str]] = {"sun": "10", "earth": "399"}
USER_AGENT: Final = "LunarHorizon-validation/0.1"
QueryKind = Literal["observer", "vectors"]


class HorizonsError(RuntimeError):
    pass


def _quoted(value: str) -> str:
    return f"'{value}'"


def site_coord(site: ObserverSite) -> str:
    altitude_km = (site.surface_height_m + site.observer_height_m) / 1000.0
    return f"{site.longitude_deg:.10f},{site.latitude_deg:.10f},{altitude_km:.12f}"


def observer_params(site: ObserverSite, body: Body, utc_calendar: str) -> dict[str, str]:
    """Azimut și elevație aparente (4), distanță și viteză radială (20); fără refracție."""
    return {
        "format": "json",
        "COMMAND": _quoted(BODY_COMMANDS[body]),
        "MAKE_EPHEM": _quoted("YES"),
        "EPHEM_TYPE": _quoted("OBSERVER"),
        "CENTER": _quoted("coord@301"),
        "COORD_TYPE": _quoted("GEODETIC"),
        "SITE_COORD": _quoted(site_coord(site)),
        "TLIST": _quoted(utc_calendar),
        "TLIST_TYPE": _quoted("CAL"),
        "TIME_TYPE": _quoted("UT"),
        "TIME_DIGITS": _quoted("FRACSEC"),
        "CAL_TYPE": _quoted("GREGORIAN"),
        "QUANTITIES": _quoted("4,20"),
        "ANG_FORMAT": _quoted("DEG"),
        "APPARENT": _quoted("AIRLESS"),
        "EXTRA_PREC": _quoted("YES"),
        "RANGE_UNITS": _quoted("KM"),
        "CSV_FORMAT": _quoted("YES"),
    }


def vector_params(site: ObserverSite, body: Body, tdb_calendar: str) -> dict[str, str]:
    """Vector geometric observator → corp în ICRF (plan FRAME), fără corecții, în km."""
    return {
        "format": "json",
        "COMMAND": _quoted(BODY_COMMANDS[body]),
        "MAKE_EPHEM": _quoted("YES"),
        "EPHEM_TYPE": _quoted("VECTORS"),
        "CENTER": _quoted("coord@301"),
        "COORD_TYPE": _quoted("GEODETIC"),
        "SITE_COORD": _quoted(site_coord(site)),
        "TLIST": _quoted(tdb_calendar),
        "TLIST_TYPE": _quoted("CAL"),
        "TIME_TYPE": _quoted("TDB"),
        "TIME_DIGITS": _quoted("FRACSEC"),
        "REF_SYSTEM": _quoted("ICRF"),
        "REF_PLANE": _quoted("FRAME"),
        "VEC_CORR": _quoted("NONE"),
        "VEC_TABLE": _quoted("1"),
        "OUT_UNITS": _quoted("KM-S"),
        "CSV_FORMAT": _quoted("YES"),
    }


def build_url(params: dict[str, str]) -> str:
    return f"{API_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


def fetch(url: str, timeout_s: float = 120.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return int(response.status), response.read()


def result_text(raw: bytes) -> str:
    """Textul tabelului din răspunsul JSON. Erorile Horizons pot veni cu HTTP 200."""
    document = json.loads(raw.decode("utf-8"))
    if "error" in document:
        raise HorizonsError(str(document["error"]))
    text = document.get("result")
    if not isinstance(text, str) or "$$SOE" not in text or "$$EOE" not in text:
        raise HorizonsError("răspuns fără tabel ($$SOE/$$EOE lipsă)")
    return text


@dataclass(frozen=True)
class ObserverRow:
    utc_calendar: str
    azimuth_deg: float
    elevation_deg: float
    range_km: float
    range_rate_km_s: float


@dataclass(frozen=True)
class VectorRow:
    jd_tdb: float
    calendar_tdb: str
    position_km: tuple[float, float, float]


def _table(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    start = lines.index("$$SOE")
    end = lines.index("$$EOE")
    header = next(
        line for line in reversed(lines[:start]) if "," in line and not line.startswith("*")
    )
    rows = [line for line in lines[start + 1 : end] if line.strip()]
    if len(rows) != 1:
        raise HorizonsError(f"se aștepta un singur rând, s-au găsit {len(rows)}")
    columns = [c.strip() for c in header.split(",")]
    values = [v.strip() for v in rows[0].split(",")]
    return columns, values


def _column(columns: list[str], values: list[str], *fragments: str) -> str:
    for name, value in zip(columns, values, strict=False):
        if all(fragment in name for fragment in fragments):
            return value
    raise HorizonsError(f"coloana {fragments} lipsește din antet: {columns}")


def parse_observer(text: str) -> ObserverRow:
    columns, values = _table(text)
    return ObserverRow(
        utc_calendar=values[0],
        azimuth_deg=float(_column(columns, values, "Azi")),
        elevation_deg=float(_column(columns, values, "Elev")),
        range_km=float(_column(columns, values, "delta")),
        range_rate_km_s=float(_column(columns, values, "deldot")),
    )


def parse_vectors(text: str) -> VectorRow:
    columns, values = _table(text)
    return VectorRow(
        jd_tdb=float(_column(columns, values, "JDTDB")),
        calendar_tdb=_column(columns, values, "Calendar"),
        position_km=(
            float(_column(columns, values, "X")),
            float(_column(columns, values, "Y")),
            float(_column(columns, values, "Z")),
        ),
    )


HEADER_KEYS: Final = (
    "Ephemeris /",
    "Target body name",
    "Center body name",
    "Center-site name",
    "Center geodetic",
    "Center cylindric",
    "Center pole/equ",
    "Center radii",
    "Target radii",
    "Reference frame",
    "Coordinate systm",
    "Output units",
    "Calendar mode",
    "Atmos refraction",
    "Rel. light bend",
    "Vis. interferer",
    "EOP file",
    "RA format",
    "Time format",
)


def header_facts(text: str) -> dict[str, str]:
    """Liniile de antet care descriu efemeridele, centrul, razele și cadrul (pentru D-18)."""
    facts: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        for key in HEADER_KEYS:
            if stripped.startswith(key) and key not in facts:
                facts[key] = stripped
    return facts
