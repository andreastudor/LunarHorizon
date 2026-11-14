"""Constante de convenție comune backendului și frontendului.

Valorile marcate „provizoriu” așteaptă confirmarea deciziei indicate din docs/STATUS.md.
Aceleași valori sunt exportate în tests/vectors/conventions.json, iar testele frontendului verifică
că `frontend/src/geo/conventions.ts` le folosește identic.
"""

from typing import Final, Literal

SCHEMA_VERSION: Final = "0.3.0"

# Cadre acceptate (docs/SPEC_FIZICA.md §3.1). Aliasurile generice nu se acceptă niciodată.
FRAME_ME_DE440: Final = "MOON_ME_DE440_ME421"
FRAME_ME_DE421: Final = "MOON_ME_DE421"
FrameId = Literal["MOON_ME_DE440_ME421", "MOON_ME_DE421"]
SUPPORTED_FRAMES: Final[tuple[str, ...]] = (FRAME_ME_DE440, FRAME_ME_DE421)
# Provizoriu: decizia D-01 [ASTRO].
DEFAULT_FRAME: Final = FRAME_ME_DE440
REJECTED_FRAME_ALIASES: Final[tuple[str, ...]] = ("MOON_ME", "MOON_PA", "IAU_MOON")

# Raza sferei de referință, în metri. Provizoriu: decizia D-05 [GEO].
REFERENCE_RADIUS_M: Final = 1_737_400.0

# Sufixele de unitate permise în numele câmpurilor numerice (docs/SPEC_FIZICA.md §1).
UNIT_SUFFIXES: Final[tuple[str, ...]] = (
    "_deg",
    "_m",
    "_km",
    "_s",
    "_utc",
    "_fraction",
    "_factor",
    "_px",
    "_bytes",
    "_count",
)

ConventionStatus = Literal["provisional", "confirmed"]
PROVISIONAL_DECISIONS: Final[dict[str, str]] = {
    "DEFAULT_FRAME": "D-01",
    "REFERENCE_RADIUS_M": "D-05",
    "POLAR_STEREOGRAPHIC": "D-06",
    "POLE_AZIMUTH_CONVENTION": "D-03",
}
