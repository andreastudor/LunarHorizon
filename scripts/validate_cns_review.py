"""Reexecutarea în motorul LunarHorizon a celor 10 comparații CN+S/Horizons primite (D-02, T-01).

Intrările sunt exact cele ale cererilor Horizons arhivate în
`data/reference/cns_review_2026_11_14/`: coordonate geodezice, altitudinea suprafeței + 2 m radial,
UTC (cu microsecunde), cadrul MOON_ME_DE440_ME421, profilul `de440_me421` (kerneluri identice ca
SHA-256 cu ale prototipului). Rezultatul se scrie separat de cel al prototipului, în
`lunarhorizon_rerun.json`.

- T-01: acceptare la separare <= 0,001° (confirmată, comunicat de utilizator);
  diagnostic > 0,00001°.
- `LT+S` se raportează numai ca diagnostic; corecția implicită este `CN+S` (D-02).
- Pentru Apollo 11 se adaugă o comparație distinctă cu altitudinea din catalogul activ (fără
  Horizons): ea nu înlocuiește altitudinea cazului de referință.
- Acordul cu Horizons nu validează coordonatele siturilor sau DEM-ul (implementări JPL înrudite).

Rulare (din rădăcină, fără rețea):
`backend\\.venv\\Scripts\\python scripts\\validate_cns_review.py`.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import spiceypy  # noqa: E402

from lunarhorizon.astro import horizons  # noqa: E402
from lunarhorizon.astro.bodies import (  # noqa: E402
    Body,
    BodyDirection,
    ObserverSite,
    body_direction_et,
)
from lunarhorizon.astro.kernels import (  # noqa: E402
    SPICE_LOCK,
    LoadedProfile,
    activate,
    load_profile,
)
from lunarhorizon.astro.reference import (  # noqa: E402
    T01_ACCEPTANCE_DEG,
    T01_DIAGNOSTIC_DEG,
    separation_deg,
    wrap_deg,
)
from lunarhorizon.catalog import load_catalog  # noqa: E402
from lunarhorizon.contracts.export import dumps  # noqa: E402
from lunarhorizon.core.conventions import (  # noqa: E402
    APPARENT_CORRECTION,
    DIAGNOSTIC_CORRECTION,
    Correction,
)
from lunarhorizon.core.coords import enu_from_az_el  # noqa: E402

ARCHIVE = ROOT / "data" / "reference" / "cns_review_2026_11_14"
OUTPUT = ARCHIVE / "lunarhorizon_rerun.json"
CATALOG_ALIASES = {"apollo11": "apollo11_lm"}  # numai situri din catalogul activ
# Unitatea astronomică (IAU 2012, exactă). Cererile pachetului nu au cerut RANGE_UNITS=KM, deci
# coloana `delta` este în au; cererile proprii ale proiectului o cer în km.
AU_KM = 149_597_870.7
BODIES: tuple[Body, ...] = ("sun", "earth")


def exact_et(utc: str) -> float:
    """ET al momentului exact al cererii (microsecunde păstrate; conversie numai prin SPICE)."""
    with SPICE_LOCK:
        return float(spiceypy.str2et(utc.rstrip("Z").replace("T", " ") + " UTC"))


def direction(
    profile: LoadedProfile, site: ObserverSite, body: Body, utc: str, correction: Correction
) -> BodyDirection:
    return body_direction_et(profile, site, body, exact_et(utc), utc, correction)


def unit(direction: tuple[float, float, float]) -> np.ndarray:
    vector = np.array(direction, dtype=float)
    result: np.ndarray = vector / float(np.linalg.norm(vector))
    return result


def main() -> int:
    cases = json.loads((ARCHIVE / "cases.json").read_text(encoding="utf-8"))["cases"]
    profile = load_profile("de440_me421")
    activate(profile)
    catalog = {site.id: site for site in load_catalog().sites}
    rows: list[dict[str, Any]] = []
    catalog_variants: list[dict[str, Any]] = []
    for case in cases:
        if case["frame_id"] != profile.frame_id:
            raise SystemExit(f"{case['case_id']}: cadru incompatibil {case['frame_id']}")
        site = ObserverSite(
            case["latitude_deg"],
            case["longitude_deg"],
            case["surface_height_m"],
            case["observer_height_m"],
        )
        for body in BODIES:
            relative = case["references"][body]
            document = json.loads((ARCHIVE / relative).read_text(encoding="utf-8"))
            raw = json.dumps(document["response"]).encode("utf-8")
            reference = horizons.parse_observer(horizons.result_text(raw))
            in_km = "RANGE_UNITS=%27KM%27" in document["url"]
            reference_range_km = reference.range_km if in_km else reference.range_km * AU_KM
            ref_unit = np.array(enu_from_az_el(reference.azimuth_deg, reference.elevation_deg))
            apparent = direction(profile, site, body, case["utc"], APPARENT_CORRECTION)
            diagnostic = direction(profile, site, body, case["utc"], DIAGNOSTIC_CORRECTION)
            separation = separation_deg(unit(apparent.direction_enu), ref_unit)
            prototype = case["prototype_results"][body]
            prototype_unit = np.array(
                enu_from_az_el(prototype["azimuth_deg"], prototype["elevation_deg"])
            )
            rows.append(
                {
                    "case_id": case["case_id"],
                    "prototype_site_id": case["prototype_site_id"],
                    "body": body,
                    "utc": case["utc"],
                    "latitude_deg": case["latitude_deg"],
                    "longitude_deg": case["longitude_deg"],
                    "surface_height_m": case["surface_height_m"],
                    "observer_height_m": case["observer_height_m"],
                    "frame_id": profile.frame_id,
                    "kernel_profile": profile.profile_id,
                    "correction": APPARENT_CORRECTION,
                    "calc_azimuth_deg": apparent.azimuth_deg,
                    "calc_elevation_deg": apparent.elevation_deg,
                    "horizons_azimuth_deg": reference.azimuth_deg,
                    "horizons_elevation_deg": reference.elevation_deg,
                    "azimuth_diff_deg": (
                        None
                        if apparent.azimuth_deg is None
                        else wrap_deg(apparent.azimuth_deg - reference.azimuth_deg)
                    ),
                    "elevation_diff_deg": apparent.elevation_deg - reference.elevation_deg,
                    "separation_deg": separation,
                    "horizons_range_units": "km"
                    if in_km
                    else "au (converted, 1 au = 149597870.7 km)",
                    "distance_diff_km": apparent.distance_km - reference_range_km,
                    "pass_T01": separation <= T01_ACCEPTANCE_DEG,
                    "above_T01_diagnostic": separation > T01_DIAGNOSTIC_DEG,
                    "lt_s_vs_cn_s_deg": separation_deg(
                        unit(diagnostic.direction_enu), unit(apparent.direction_enu)
                    ),
                    "lt_s_separation_vs_horizons_deg": separation_deg(
                        unit(diagnostic.direction_enu), ref_unit
                    ),
                    "prototype_separation_vs_horizons_deg": prototype["separation_vs_horizons_deg"],
                    "lunarhorizon_vs_prototype_deg": separation_deg(
                        unit(apparent.direction_enu), prototype_unit
                    ),
                }
            )
        catalog_id = CATALOG_ALIASES.get(case["prototype_site_id"])
        entry = catalog.get(catalog_id) if catalog_id else None
        if entry is not None and entry.elevation_m is not None:
            alternative = ObserverSite(
                entry.latitude_deg,
                entry.longitude_deg,
                float(entry.elevation_m),
                case["observer_height_m"],
            )
            for body in BODIES:
                a = direction(profile, site, body, case["utc"], APPARENT_CORRECTION)
                b = direction(profile, alternative, body, case["utc"], APPARENT_CORRECTION)
                catalog_variants.append(
                    {
                        "case_id": case["case_id"],
                        "body": body,
                        "reference_surface_height_m": case["surface_height_m"],
                        "catalog_id": entry.id,
                        "catalog_elevation_m": float(entry.elevation_m),
                        "separation_catalog_vs_reference_height_deg": separation_deg(
                            unit(a.direction_enu), unit(b.direction_enu)
                        ),
                    }
                )
    worst = max(rows, key=lambda r: r["separation_deg"])
    above = [f"{r['case_id']}/{r['body']}" for r in rows if r["above_T01_diagnostic"]]
    summary: dict[str, Any] = {
        "comparisons": len(rows),
        "all_pass_T01": all(r["pass_T01"] for r in rows),
        "above_diagnostic": above,
        "max_separation_deg": worst["separation_deg"],
        "max_separation_case": f"{worst['case_id']}/{worst['body']}",
        "max_lt_s_vs_cn_s_deg": max(r["lt_s_vs_cn_s_deg"] for r in rows),
        "max_abs_distance_diff_km": max(abs(r["distance_diff_km"]) for r in rows),
        "max_lunarhorizon_vs_prototype_deg": max(r["lunarhorizon_vs_prototype_deg"] for r in rows),
        "prototype_max_separation_deg": max(
            r["prototype_separation_vs_horizons_deg"] for r in rows
        ),
    }
    report: dict[str, Any] = {
        "description": (
            "LunarHorizon engine re-run of the 10 CN+S/Horizons comparisons of the evidence "
            "package (same coordinates, heights, UTC, frame; kernel profile de440_me421). Reported "
            "separately from the prototype results. Agreement with Horizons does not validate site "
            "coordinates or DEM data."
        ),
        "decisions": {
            "D-02": "CN+S default apparent correction; LT+S diagnostic only; NONE for geometry",
            "T-01": "acceptance separation <= 0.001 deg; diagnostic > 0.00001 deg on the fixed set",
            "status": "confirmed by the astronomers, communicated by the user in the conversation",
        },
        "thresholds_deg": {
            "T01_acceptance": T01_ACCEPTANCE_DEG,
            "T01_diagnostic": T01_DIAGNOSTIC_DEG,
        },
        "summary": summary,
        "comparisons": rows,
        "catalog_height_variants": {
            "note": (
                "Engine-only comparison: the same case with the active catalog elevation instead "
                "of the reference-case surface height. Horizons was not queried for that elevation."
            ),
            "rows": catalog_variants,
        },
    }
    OUTPUT.write_text(dumps(report), encoding="utf-8", newline="\n")
    status = "trecut" if summary["all_pass_T01"] else "EȘUAT"
    print(
        f"{summary['comparisons']} comparații CN+S: T-01 {status}, "
        f"separare max {summary['max_separation_deg']:.3e}° ({summary['max_separation_case']}); "
        f"peste diagnostic: {above or 'niciuna'}; "
        f"LT+S vs CN+S max {summary['max_lt_s_vs_cn_s_deg']:.3e}°; "
        f"față de prototip max {summary['max_lunarhorizon_vs_prototype_deg']:.3e}°"
    )
    print(f"scris: {OUTPUT.relative_to(ROOT)}")
    return 0 if summary["all_pass_T01"] else 1


if __name__ == "__main__":
    sys.exit(main())
