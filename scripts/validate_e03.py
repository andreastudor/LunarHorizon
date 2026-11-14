"""Raportul de validare E03: motorul local față de referințele Horizons arhivate.

Rulare din rădăcina repository-ului (fără rețea; cere kernelurile din data/kernels):
    backend\\.venv\\Scripts\\python scripts\\validate_e03.py

Scrie data/reference/horizons/e03_comparison.json: fiecare comparație (corecții LT+S și CN+S,
profilurile DE440 și DE421, vectori ICRF), diferențele dintre profiluri (T-03), antetele Horizons
relevante pentru D-18 și maximele. Pragurile din raport sunt PROPUSE și nevalidate.
"""

import dataclasses
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import spiceypy  # noqa: E402

from lunarhorizon.astro import reference as ref  # noqa: E402
from lunarhorizon.astro.bodies import Correction, body_direction  # noqa: E402
from lunarhorizon.astro.kernels import LoadedProfile, activate, load_profile  # noqa: E402
from lunarhorizon.contracts.export import dumps  # noqa: E402

OUTPUT = ref.REFERENCE_DIR / "e03_comparison.json"


def _maxima(rows: list[dict[str, Any]]) -> dict[str, Any]:
    validation = [r for r in rows if not r["diagnostic"]]
    worst = max(validation, key=lambda r: r["separation_deg"])
    worst_distance = max(validation, key=lambda r: abs(r["distance_diff_km"]))
    return {
        "count": len(validation),
        "max_separation_deg": worst["separation_deg"],
        "max_separation_case": f"{worst['case_id']}/{worst['body']}",
        "max_abs_distance_diff_km": abs(worst_distance["distance_diff_km"]),
        "max_abs_distance_case": f"{worst_distance['case_id']}/{worst_distance['body']}",
        "within_proposed_T01": all(
            r["separation_deg"] <= ref.PROPOSED_TOLERANCES["T-01_separation_deg"]
            for r in validation
        ),
        "within_proposed_T02": all(
            abs(r["distance_diff_km"]) <= ref.PROPOSED_TOLERANCES["T-02_distance_km"]
            for r in validation
        ),
    }


def main() -> int:
    cases = ref.load_cases()
    de440 = load_profile("de440_me421")
    de421 = load_profile("de421")
    report: dict[str, Any] = {
        "description": (
            "Comparația motorului LunarHorizon (SPICE, kerneluri locale) cu răspunsurile "
            "JPL Horizons "
            "arhivate. Acord între două implementări JPL (DE440s local, DE441 la Horizons), nu "
            "validare prin observații independente. Pragurile sunt propuse, nevalidate (D-12)."
        ),
        "environment": {
            "spiceypy": spiceypy.__version__,
            "cspice": spiceypy.tkvrsn("TOOLKIT"),
        },
        "proposed_tolerances": ref.PROPOSED_TOLERANCES,
        "proposed_tolerances_status": "NEVALIDAT",
        "profiles": {
            p.profile_id: {
                "frame_id": p.frame_id,
                "coverage_start_utc": p.coverage_start_utc,
                "coverage_end_utc": p.coverage_end_utc,
            }
            for p in (de440, de421)
        },
        "horizons_header_example": ref.header_summary("a11_dem", "sun"),
        "horizons_vector_header_example": ref.header_summary("a11_catalog", "earth", "vectors"),
    }

    groups: dict[str, list[dict[str, Any]]] = {}
    runs: tuple[tuple[str, LoadedProfile, Correction], ...] = (
        ("de440_LT+S", de440, "LT+S"),
        ("de440_CN+S", de440, "CN+S"),
        ("de421_LT+S", de421, "LT+S"),
    )
    for label, profile, correction in runs:
        activate(profile)
        groups[label] = [
            dataclasses.asdict(ref.compare_direction(profile, case, body, correction))
            for case in cases
            for body in ("sun", "earth")
        ]
    report["direction_comparisons"] = groups
    report["direction_summary"] = {label: _maxima(rows) for label, rows in groups.items()}

    activate(de440)
    vector_case = next(c for c in cases if "vectors" in c.queries)
    vectors = [
        dataclasses.asdict(ref.compare_vector(de440, vector_case, b)) for b in ("sun", "earth")
    ]
    report["vector_comparisons"] = vectors
    report["vector_summary"] = {
        "max_vector_diff_km": max(v["vector_diff_km"] for v in vectors),
        "within_proposed": all(
            v["vector_diff_km"] <= ref.PROPOSED_TOLERANCES["T-02_vector_km"] for v in vectors
        ),
    }

    t03: list[dict[str, Any]] = []
    for case in cases:
        for body in ("sun", "earth"):
            a = body_direction(de440, case.site, body, case.utc)
            b = body_direction(de421, case.site, body, case.utc)
            t03.append(
                {
                    "case_id": case.case_id,
                    "body": body,
                    "separation_deg": ref.separation_deg(
                        np.array(a.direction_enu), np.array(b.direction_enu)
                    ),
                    "distance_diff_km": a.distance_km - b.distance_km,
                }
            )
    report["t03_profile_differences"] = t03
    report["t03_summary"] = {
        "max_separation_deg": max(r["separation_deg"] for r in t03),
        "max_abs_distance_diff_km": max(abs(r["distance_diff_km"]) for r in t03),
    }
    activate(de440)

    OUTPUT.write_text(dumps(report), encoding="utf-8", newline="\n")
    for label, summary in report["direction_summary"].items():
        print(
            f"{label}: {summary['count']} comparații, "
            f"separare max {summary['max_separation_deg']:.3e}° "
            f"({summary['max_separation_case']}), "
            f"|ΔD| max {summary['max_abs_distance_diff_km']:.4f} km"
        )
    print(f"vectori ICRF: |Δv| max {report['vector_summary']['max_vector_diff_km'] * 1000:.3f} m")
    print(f"T-03: separare max {report['t03_summary']['max_separation_deg']:.3e}°")
    print(f"scris: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
