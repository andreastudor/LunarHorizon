"""Studiul de convergență al orizontului din DEM (E09, testul T-07 din docs/VALIDARE.md).

Pentru punctul reprezentativ Leibnitz Beta (studiu complet) și pentru alte puncte DEM (studiu
redus) se calculează profilul H(a) cu configurații care diferă printr-un singur parametru:

- pasul radial al nivelului apropiat și al celui îndepărtat (dublare / înjumătățire);
- rezoluția nivelului îndepărtat (LDEM_75S_120M față de LDEM_75S_60M, dacă există pe disc);
- rezoluția nivelului apropiat (rasterul de 5 m față de media pe blocuri 2x2, adică 10 m);
- raza de căutare `d_max` (25-400 km), cu acoperirea raportată: o rază care depășește datele
  disponibile NU poate demonstra convergența fizică;
- pasul azimutal `Δa`, față de un profil de referință cu 0,1°, interpolat liniar ca în serviciu.

Metricile: max, p95 și RMS ale |ΔH| pe azimuturi, numărul azimuturilor peste prag, timpul de
calcul, acoperirea. Rezultatul se scrie în `data/reference/horizon/e09_convergence.json`.
Pragul este o propunere tehnică (D-08/D-09 [GEO] deschise), nu o toleranță validată.

Utilizare (din rădăcină): `backend\\.venv\\Scripts\\python scripts\\horizon_convergence.py`.
"""

import itertools
import json
import math
import platform
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.api.horizon import DEFAULT_PARAMETERS  # noqa: E402
from lunarhorizon.terrain.horizon import (  # noqa: E402
    ALGORITHM_VERSION,
    ComputedHorizon,
    HeightGrid,
    HorizonParameters,
    compute_horizon,
    interpolate_horizon,
    load_geotiff_grid,
)
from lunarhorizon.terrain.lola_gdr import load_lola_polar_grid  # noqa: E402

RAW = ROOT / "data" / "_raw" / "lola_gdr"
CACHE = ROOT / "data" / "_cache" / "terrain"
OUTPUT = ROOT / "data" / "reference" / "horizon" / "e09_convergence.json"
FRAME = "MOON_ME_DE421"
RADIUS = 1_737_400.0
EQUIPMENT_M = 2.0
# Propunere tehnică: o cincime din raza unghiulară a Soarelui (≈ 0,267°). Nevalidat (D-08/D-09).
THRESHOLD_DEG = 0.05
POINTS = {
    "leibnitz_beta": (-85.4266039743, 31.7441821732, "leibnitz_beta", "pgda104_leibnitz_beta"),
    "haworth": (-86.76404982027084, -22.776243241756063, "haworth", "pgda104_haworth"),
    "peak_near_shackleton": (
        -88.8109,
        123.6912,
        "peak_near_shackleton",
        "pgda104_peak_near_shackleton",
    ),
}


def near_grid(slug: str, product_id: str) -> HeightGrid:
    return load_geotiff_grid(
        CACHE / slug / "calculation.tif", product_id, "near", FRAME, RADIUS, None
    )


def far_grid(name: str) -> HeightGrid | None:
    label, image = RAW / f"{name}.LBL", RAW / f"{name}.IMG"
    if not (label.is_file() and image.is_file()):
        return None
    return load_lola_polar_grid(label, image, f"lola_gdr_{name.lower()}", None)


def coarsen(grid: HeightGrid) -> HeightGrid:
    """Media pe blocuri 2x2 (rezoluție dublă); NaN se propagă (fără umplere)."""
    heights = np.asarray(grid.heights, dtype=np.float64)
    rows, cols = (s // 2 * 2 for s in heights.shape)
    blocks = heights[:rows, :cols].reshape(rows // 2, 2, cols // 2, 2).mean(axis=(1, 3))
    return replace(
        grid,
        product_id=grid.product_id + "_10m",
        heights=blocks.astype(np.float32),
        resolution_m=grid.resolution_m * 2,
        x_first_m=grid.x_first_m + grid.resolution_m / 2,
        y_first_m=grid.y_first_m - grid.resolution_m / 2,
    )


def observer_height(grid: HeightGrid, lat: float, lon: float) -> float:
    x, y = grid.project(np.radians(np.array([lat])), np.radians(np.array([lon])))
    value = float(grid.sample(x, y)[0])
    if not math.isfinite(value):
        raise SystemExit("altitudinea observatorului este necunoscută")
    return value


def run(
    lat: float, lon: float, h0: float, tiers: Sequence[HeightGrid], p: HorizonParameters
) -> ComputedHorizon:
    return compute_horizon(lat, lon, h0, EQUIPMENT_M, tiers, p)


def summary(result: ComputedHorizon, near_reach_m: float) -> dict[str, Any]:
    distances = [d for d in result.obstacle_distance_m if d is not None]
    return {
        "compute_time_s": round(result.compute_time_s, 3),
        "samples_per_azimuth": result.samples_per_azimuth,
        "coverage_fraction": round(result.coverage_fraction, 6),
        "azimuths_complete": sum(q == "complete" for q in result.quality),
        "azimuths_partial": sum(q == "partial" for q in result.quality),
        "azimuths_no_data": sum(q == "no_data" for q in result.quality),
        "product_fractions": {k: round(v, 4) for k, v in result.product_fractions.items()},
        "obstacle_distance_max_m": round(max(distances), 1) if distances else None,
        "azimuths_with_obstacle_beyond_near_raster": sum(d > near_reach_m for d in distances),
    }


def compare(a: ComputedHorizon, b: ComputedHorizon) -> dict[str, Any]:
    """|ΔH| pe azimuturile comune (același pas), numai unde ambele au valoare."""
    pairs = [
        (x, y)
        for x, y in zip(a.elevation_deg, b.elevation_deg, strict=True)
        if x is not None and y is not None
    ]
    diff = np.abs(np.array([x - y for x, y in pairs]))
    return metrics(diff)


def metrics(diff: np.ndarray) -> dict[str, Any]:
    return {
        "max_abs_delta_deg": round(float(diff.max()), 5),
        "p95_abs_delta_deg": round(float(np.percentile(diff, 95)), 5),
        "rms_delta_deg": round(float(np.sqrt(np.mean(diff**2))), 5),
        "azimuths_over_threshold": int((diff > THRESHOLD_DEG).sum()),
        "azimuths_compared": int(diff.size),
    }


def near_reach(grid: HeightGrid, lat: float, lon: float) -> float:
    x, y = grid.project(np.radians(np.array([lat])), np.radians(np.array([lon])))
    x0, y0, x1, y1 = grid.bounds_m()
    # Distanța minimă până la marginea rasterului; dincolo de ea obstacolul vine din nivelul
    # îndepărtat.
    return min(float(x[0]) - x0, x1 - float(x[0]), float(y[0]) - y0, y1 - float(y[0]))


def required_height_beyond(result: ComputedHorizon, h0: float, d_max_m: float) -> dict[str, Any]:
    """Înălțimea minimă (față de sferă) a unui obstacol aflat la `d_max` care ar ridica H(a) pe
    azimutul cu orizontul cel mai jos: (R + h)·(cos δ - tan H·sin δ) = r_obs. Dincolo de `d_max`
    înălțimea necesară crește. Nu presupune nimic despre terenul real de acolo."""
    values = [v for v in result.elevation_deg if v is not None]
    lowest = min(values)
    delta = d_max_m / RADIUS
    r_obs = RADIUS + h0 + EQUIPMENT_M
    needed = r_obs / (math.cos(delta) - math.tan(math.radians(lowest)) * math.sin(delta)) - RADIUS
    return {
        "lowest_horizon_deg": round(lowest, 4),
        "d_max_m": d_max_m,
        "required_obstacle_height_m": round(needed, 1),
    }


def study(name: str, full: bool, far120: HeightGrid, far60: HeightGrid | None) -> dict[str, Any]:
    lat, lon, slug, product_id = POINTS[name]
    near = near_grid(slug, product_id)
    h0 = observer_height(near, lat, lon)
    reach = near_reach(near, lat, lon)
    base = replace(DEFAULT_PARAMETERS, azimuth_step_deg=1.0)
    out: dict[str, Any] = {
        "latitude_deg": lat,
        "longitude_deg": lon,
        "observer_terrain_elevation_m": round(h0, 3),
        "observer_height_m": EQUIPMENT_M,
        "near_raster_min_edge_distance_m": round(reach, 1),
        "base_parameters": base.as_dict(),
    }
    tiers = [near, far120]
    reference = run(lat, lon, h0, tiers, base)
    out["base"] = summary(reference, reach)

    # d_max: 25 … 400 km; comparat cu raza următoare.
    radii_km = [25, 50, 100, 150, 200, 250, 300, 350, 400] if full else [100, 200, 300, 400]
    rows: list[dict[str, Any]] = []
    results = {r: run(lat, lon, h0, tiers, replace(base, d_max_m=r * 1000.0)) for r in radii_km}
    for low, high in itertools.pairwise(radii_km):
        rows.append(
            {
                "d_max_km": low,
                "vs_d_max_km": high,
                **compare(results[low], results[high]),
                **summary(results[high], reach),
            }
        )
    out["d_max"] = rows
    out["beyond_d_max_bound"] = {
        **required_height_beyond(results[300], h0, 300_000.0),
        "far_product_max_height_m": round(float(np.max(far120.heights)) * far120.scale, 1),
        "note": "max of LDEM_75S_120M over its whole grid; terrain beyond the grid is not covered",
    }

    # Rezoluția nivelului îndepărtat: 120 m față de 60 m (pas radial egal cu rezoluția).
    if far60 is not None:
        r60 = run(lat, lon, h0, [near, far60], replace(base, far_step_m=60.0))
        r120_60 = run(lat, lon, h0, tiers, replace(base, far_step_m=60.0))
        out["far_resolution"] = {
            "LDEM_75S_120M_step_120_vs_LDEM_75S_60M_step_60": {
                **compare(reference, r60),
                **summary(r60, reach),
            },
            "LDEM_75S_120M_step_60_vs_LDEM_75S_60M_step_60": compare(r120_60, r60),
        }

    if full:
        out["near_step"] = []
        for coarse, fine in ((10.0, 5.0), (5.0, 2.5)):
            a = run(lat, lon, h0, tiers, replace(base, near_step_m=coarse, d_min_m=fine))
            b = run(lat, lon, h0, tiers, replace(base, near_step_m=fine, d_min_m=fine))
            out["near_step"].append(
                {
                    "near_step_m": coarse,
                    "vs_near_step_m": fine,
                    **compare(a, b),
                    **summary(b, reach),
                }
            )
        out["far_step"] = []
        for coarse, fine in ((240.0, 120.0), (120.0, 60.0)):
            a = run(lat, lon, h0, tiers, replace(base, far_step_m=coarse))
            b = run(lat, lon, h0, tiers, replace(base, far_step_m=fine))
            out["far_step"].append(
                {"far_step_m": coarse, "vs_far_step_m": fine, **compare(a, b), **summary(b, reach)}
            )
        coarse_near = coarsen(near)
        r10 = run(
            lat, lon, h0, [coarse_near, far120], replace(base, near_step_m=10.0, d_min_m=10.0)
        )
        r5 = run(lat, lon, h0, tiers, replace(base, d_min_m=10.0))
        out["near_resolution"] = {
            "near_10m_block_mean_vs_5m": compare(r10, r5),
            "note": "same observer height; d_min 10 m in both",
        }

        ref_step = 0.1
        ref = run(lat, lon, h0, tiers, replace(base, azimuth_step_deg=ref_step))
        ref_az = np.arange(ref.elevation_deg.__len__()) * ref_step
        out["azimuth_step"] = []
        for step in (2.0, 1.0, 0.5, 0.25):
            coarse_profile = run(lat, lon, h0, tiers, replace(base, azimuth_step_deg=step))
            diffs = []
            for az, value in zip(ref_az, ref.elevation_deg, strict=True):
                estimate = interpolate_horizon(coarse_profile.elevation_deg, step, float(az))
                if value is not None and estimate is not None:
                    diffs.append(abs(estimate - value))
            out["azimuth_step"].append(
                {
                    "azimuth_step_deg": step,
                    "vs_reference_step_deg": ref_step,
                    **metrics(np.array(diffs)),
                    "compute_time_s": round(coarse_profile.compute_time_s, 3),
                }
            )
        out["azimuth_step_reference_time_s"] = round(ref.compute_time_s, 3)
        proposed = run(lat, lon, h0, tiers, DEFAULT_PARAMETERS)
        out["proposed_parameters"] = {
            "parameters": DEFAULT_PARAMETERS.as_dict(),
            **summary(proposed, reach),
        }
    return out


def main() -> int:
    far120 = far_grid("LDEM_75S_120M")
    if far120 is None:
        print("LDEM_75S_120M lipsește: rulați scripts/acquire_lola_gdr.py LDEM_75S_120M")
        return 1
    far60 = far_grid("LDEM_75S_60M")
    report: dict[str, Any] = {
        "description": (
            "E09 horizon convergence study (T-07). Technical proposal; D-08/D-09 [GEO] open."
        ),
        "generated_at_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "algorithm_version": ALGORITHM_VERSION,
        "threshold_deg": THRESHOLD_DEG,
        "threshold_status": (
            "provisional technical proposal (1/5 of the solar angular radius), not validated"
        ),
        "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
        "far_products": {"LDEM_75S_120M": True, "LDEM_75S_60M": far60 is not None},
        "points": {},
    }
    for name in POINTS:
        if not (CACHE / POINTS[name][2] / "calculation.tif").is_file():
            continue
        print(f"{name} …", flush=True)
        report["points"][name] = study(
            name, full=(name == "leibnitz_beta"), far120=far120, far60=far60
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scris: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
