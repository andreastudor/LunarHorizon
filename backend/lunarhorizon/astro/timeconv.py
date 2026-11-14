"""Conversia UTC ↔ ET (TDB) numai prin SPICE și verificarea acoperirii (docs/SPEC_FIZICA.md §2).

Lanțul UTC → TAI → TT → TDB este calculat de SPICE, cu kernelul de secunde intercalare încărcat.
Nu se face aritmetică proprie între scările de timp.
"""

from typing import Final

import spiceypy

from lunarhorizon.astro.kernels import SPICE_LOCK, LoadedProfile, activate
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.core.utc import canonical_utc, parse_utc

# Marja față de capetele acoperirii: corecția de timp de lumină evaluează ținta mai devreme
# (cel mult ~500 s pentru Soare), deci momentul cerut trebuie să fie departe de margini.
LIGHT_TIME_MARGIN_S: Final = 600.0


def spice_time_string(utc: str) -> str:
    """Forma ISO fără zonă, interpretată de SPICE ca UTC: YYYY-MM-DDTHH:MM:SS.fff."""
    moment = parse_utc(utc)
    return (
        f"{moment.year:04d}-{moment.month:02d}-{moment.day:02d}T"
        f"{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d}."
        f"{moment.microsecond // 1000:03d}"
    )


def utc_to_et(utc: str, profile: LoadedProfile) -> float:
    activate(profile)
    with SPICE_LOCK:
        return float(spiceypy.str2et(spice_time_string(utc)))


def et_to_utc(et: float, profile: LoadedProfile) -> str:
    activate(profile)
    with SPICE_LOCK:
        return canonical_utc(f"{spiceypy.et2utc(et, 'ISOC', 3)}Z")


def et_to_tdb_calendar(et: float, profile: LoadedProfile) -> str:
    """Momentul în TDB, ca text calendaristic (pentru cererile Horizons cu TIME_TYPE=TDB)."""
    activate(profile)
    with SPICE_LOCK:
        return str(spiceypy.timout(et, "YYYY-MM-DD HR:MN:SC.###### ::TDB"))


def require_in_coverage(
    et: float, profile: LoadedProfile, margin_s: float = LIGHT_TIME_MARGIN_S
) -> None:
    if not (profile.coverage_start_et + margin_s <= et <= profile.coverage_end_et - margin_s):
        raise LunarHorizonError(
            ErrorCode.OUT_OF_EPHEMERIS_COVERAGE,
            f"momentul este în afara acoperirii profilului {profile.profile_id} "
            f"({profile.coverage_start_utc} - {profile.coverage_end_utc}, marjă {margin_s:.0f} s)",
            context={
                "coverage_start_utc": canonical_utc(profile.coverage_start_utc),
                "coverage_end_utc": canonical_utc(profile.coverage_end_utc),
            },
        )
