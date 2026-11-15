"""Studiul de convergență al vizibilității E10 (disc solar D-04, Pământ, evenimente), date reale.

Punctul Leibnitz Beta, 30 de zile, modul `dem`. Variază câte un parametru față de configurația de
bază (profil fin 0,025°, scanare 60 s / 300 s, 128 de coloane pe disc):

- pasul azimutal al profilului folosit pentru vizibilitate: 0,05°, 0,025°, 0,0125°;
- pasul scanării pentru Soare: 120 s, 60 s, 30 s;
- numărul de coloane de integrare a discului: 64, 128, 256 (fracția la momentele seriei).

Metrici: deplasarea maximă a momentelor evenimentelor (aceleași tipuri, în ordine), diferența
duratelor vizibile și necunoscute, diferența maximă a fracției vizibile, timpul de calcul.
Rezultatul se scrie în `data/reference/visibility/e10_convergence.json`. Precizia numerică nu este
incertitudine fizică (DEM).

Rulare (din rădăcină): `backend\\.venv\\Scripts\\python scripts\\visibility_convergence.py`.
"""

import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.api.data import DataRegistry  # noqa: E402
from lunarhorizon.api.horizon import (  # noqa: E402
    DEFAULT_PARAMETERS,
    VISIBILITY_PARAMETERS,
    HorizonService,
)
from lunarhorizon.api.settings import Settings  # noqa: E402
from lunarhorizon.contracts.simulation import SimulationRequest, SimulationResult  # noqa: E402
from lunarhorizon.core.utc import parse_utc  # noqa: E402
from lunarhorizon.simulation import idealized  # noqa: E402
from lunarhorizon.simulation.idealized import DemSiteInput, simulate_idealized  # noqa: E402
from lunarhorizon.simulation.service import prepare_request  # noqa: E402
from lunarhorizon.simulation.visibility import HorizonModel, sun_visibility  # noqa: E402

OUTPUT = ROOT / "data" / "reference" / "visibility" / "e10_convergence.json"


def seconds(utc: str) -> float:
    return parse_utc(utc).timestamp()


def events(result: SimulationResult, body: str) -> list[tuple[str, float]]:
    group = getattr(result.events[0], body)
    return [(e.type, seconds(e.time_utc)) for e in group.events]


def compare(a: SimulationResult, b: SimulationResult) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for body in ("sun", "earth"):
        ea, eb = events(a, body), events(b, body)
        same = [x[0] for x in ea] == [x[0] for x in eb]
        out[f"{body}_events"] = [len(ea), len(eb)]
        out[f"{body}_same_event_sequence"] = same
        out[f"{body}_max_event_shift_s"] = (
            round(max((abs(x[1] - y[1]) for x, y in zip(ea, eb, strict=True)), default=0.0), 3)
            if same
            else None
        )
    sa, sb = a.summary[0], b.summary[0]
    out["sun_visible_duration_diff_s"] = round(
        abs((sa.sun_visible_duration_s or 0) - (sb.sun_visible_duration_s or 0)), 3
    )
    out["earth_visible_duration_diff_s"] = round(
        abs((sa.earth_visible_duration_s or 0) - (sb.earth_visible_duration_s or 0)), 3
    )
    out["sun_unknown_duration_s"] = [sa.sun_unknown_duration_s, sb.sun_unknown_duration_s]
    fa, fb = a.series[0].sun.visible_fraction, b.series[0].sun.visible_fraction
    diffs = [abs(x - y) for x, y in zip(fa, fb, strict=True) if x is not None and y is not None]
    out["sun_fraction_max_diff"] = round(max(diffs, default=0.0), 5)
    return out


def main() -> int:
    settings = Settings()
    registry = DataRegistry(settings)
    service = HorizonService(registry, settings.far_terrain_dir, settings.horizon_cache_dir)
    site = next(s for s in registry.catalog().sites if "leibnitz" in s.id)
    raw = {
        "sites": [{"site_id": site.id}],
        "frame_id": site.frame_id,
        "start_utc": "2026-11-15T00:00:00Z",
        "end_utc": "2026-12-15T00:00:00Z",
        "observer_height_m": 2.0,
        "solar_criterion": "disc_positive_area",
        "earth_criterion": {"kind": "center_above_horizon", "min_elevation_deg": 0.0},
        "terrain_mode": "dem",
        "series_step_s": 3600,
    }
    request, sites = prepare_request(
        SimulationRequest.model_validate(raw), registry.catalog(), 366, 20_000
    )
    kernel = registry.profile_for_frame(request.frame_id)
    selection = registry.select_terrain(site.latitude_deg, site.longitude_deg, request.frame_id)
    assert selection.entry is not None
    coarse = service.profile(site.latitude_deg, site.longitude_deg, request.frame_id, 2.0)

    def run(step_deg: float) -> tuple[SimulationResult, float, float]:
        started = time.perf_counter()
        fine = service.profile(
            site.latitude_deg,
            site.longitude_deg,
            request.frame_id,
            2.0,
            replace(VISIBILITY_PARAMETERS, azimuth_step_deg=step_deg),
        )
        profile_s = time.perf_counter() - started
        dem = {sites[0].site_ref: DemSiteInput(coarse, selection.entry.manifest, fine)}  # type: ignore[union-attr]
        started = time.perf_counter()
        result = simulate_idealized(request, sites, kernel, None, dem)
        return result, profile_s, time.perf_counter() - started

    report: dict[str, Any] = {
        "description": (
            "E10 visibility convergence (Leibnitz Beta, 30 days, DEM mode). Numerical precision "
            "of the algorithm, not physical (DEM, ephemeris) uncertainty."
        ),
        "base": {
            "visibility_azimuth_step_deg": VISIBILITY_PARAMETERS.azimuth_step_deg,
            "horizon_parameters": DEFAULT_PARAMETERS.as_dict(),
            "scan_step_s": idealized.SCAN_STEP_S["dem"],
            "refinement_tolerance_s": idealized.REFINEMENT_TOLERANCE_S,
        },
    }
    base, base_profile_s, base_run_s = run(0.025)
    report["base_timing_s"] = {
        "fine_profile": round(base_profile_s, 2),
        "simulation": round(base_run_s, 2),
    }
    report["base_summary"] = {
        "sun_events": [(t, e) for t, e in events(base, "sun")],
        "earth_events": [(t, e) for t, e in events(base, "earth")],
        "sun_visible_duration_s": base.summary[0].sun_visible_duration_s,
        "sun_unknown_duration_s": base.summary[0].sun_unknown_duration_s,
        "earth_visible_duration_s": base.summary[0].earth_visible_duration_s,
        "both_visible_duration_s": base.summary[0].both_visible_duration_s,
        "criterion_evaluations": base.provenance.event_parameters["criterion_evaluations"],
    }

    report["profile_step"] = []
    for step in (0.05, 0.0125):
        result, profile_s, run_s = run(step)
        print(f"profil {step}° …", flush=True)
        report["profile_step"].append(
            {
                "azimuth_step_deg": step,
                "vs_deg": 0.025,
                **compare(result, base),
                "fine_profile_s": round(profile_s, 2),
                "simulation_s": round(run_s, 2),
            }
        )

    report["sun_scan_step"] = []
    original = dict(idealized.SCAN_STEP_S["dem"])
    try:
        for step in (120.0, 30.0):
            idealized.SCAN_STEP_S["dem"]["sun"] = step
            result, _, run_s = run(0.025)
            print(f"scanare Soare {step} s …", flush=True)
            report["sun_scan_step"].append(
                {
                    "sun_scan_step_s": step,
                    "vs_s": 60.0,
                    **compare(result, base),
                    "simulation_s": round(run_s, 2),
                }
            )
    finally:
        idealized.SCAN_STEP_S["dem"].update(original)

    fine = service.profile(
        site.latitude_deg, site.longitude_deg, request.frame_id, 2.0, VISIBILITY_PARAMETERS
    )
    model = HorizonModel.from_profile(fine)
    sun = base.series[0].sun
    columns: dict[int, list[float | None]] = {}
    for count in (64, 128, 256):
        columns[count] = [
            sun_visibility(model, az, el, rho, count).fraction
            for az, el, rho in zip(
                sun.azimuth_deg, sun.elevation_deg, sun.angular_radius_deg, strict=True
            )
        ]
    report["disc_columns"] = []
    for count in (64, 256):
        diffs = [
            abs(x - y)
            for x, y in zip(columns[count], columns[128], strict=True)
            if x is not None and y is not None
        ]
        report["disc_columns"].append(
            {
                "columns": count,
                "vs_columns": 128,
                "fraction_max_diff": round(max(diffs, default=0.0), 6),
            }
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scris: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
