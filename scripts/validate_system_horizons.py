"""E10A centre vectors against archived geometric Horizons responses; --fetch uses JPL."""

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.astro import horizons  # noqa: E402
from lunarhorizon.astro.kernels import load_profile  # noqa: E402
from lunarhorizon.astro.system import system_series  # noqa: E402
from lunarhorizon.astro.timeconv import et_to_tdb_calendar, utc_to_et  # noqa: E402
from lunarhorizon.contracts.system import SystemRequest  # noqa: E402

REFERENCE = ROOT / "data/reference/system_horizons"
EPOCHS = ["2026-11-15T00:00:00Z", "2026-12-15T00:00:00Z"]
# Existing T-02 comparison threshold, used as an engineering check here, not ASTRO approval.
THRESHOLD_KM = 0.1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    profile = load_profile("de440_me421")
    result = system_series(profile, SystemRequest(time_utc=EPOCHS))
    REFERENCE.mkdir(parents=True, exist_ok=True)
    comparisons: list[dict[str, object]] = []
    for i, utc in enumerate(EPOCHS):
        vectors: dict[str, list[float]] = {"sun": [0.0, 0.0, 0.0]}
        for body, command in (("earth", "399"), ("moon", "301")):
            stem = REFERENCE / f"{utc[:10]}_{body}"
            response_path = stem.with_suffix(".response.json")
            request_path = stem.with_suffix(".request.json")
            if args.fetch and not response_path.exists():
                tdb = et_to_tdb_calendar(utc_to_et(utc, profile), profile)
                values = {
                    "COMMAND": command,
                    "CENTER": "500@10",
                    "MAKE_EPHEM": "YES",
                    "EPHEM_TYPE": "VECTORS",
                    "TLIST": tdb,
                    "TLIST_TYPE": "CAL",
                    "TIME_TYPE": "TDB",
                    "REF_SYSTEM": "ICRF",
                    "REF_PLANE": "FRAME",
                    "VEC_CORR": "NONE",
                    "VEC_TABLE": "1",
                    "OUT_UNITS": "KM-S",
                    "CSV_FORMAT": "YES",
                    "TIME_DIGITS": "FRACSEC",
                }
                params = {key: f"'{value}'" for key, value in values.items()}
                params["format"] = "json"
                url = horizons.build_url(params)
                status, raw = horizons.fetch(url, timeout_s=45)
                horizons.parse_vectors(horizons.result_text(raw))
                response_path.write_bytes(raw)
                request_path.write_text(
                    json.dumps(
                        {
                            "url": url,
                            "params": params,
                            "utc": utc,
                            "retrieved_at_utc": datetime.now(UTC).isoformat(),
                            "http_status": status,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            raw = response_path.read_bytes()
            record = json.loads(request_path.read_text(encoding="utf-8"))
            if hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ValueError("Archived Horizons response checksum mismatch")
            text = horizons.result_text(raw)
            facts = horizons.header_facts(text)
            if "Sun (10)" not in facts.get("Center body name", ""):
                raise ValueError("Horizons origin is not the solar centre")
            if "ICRF" not in facts.get("Reference frame", ""):
                raise ValueError("Horizons reference axes are not ICRF")
            if "GEOMETRIC" not in text or "KM-S" not in text:
                raise ValueError("Expected geometric vectors in km")
            vectors[body] = list(horizons.parse_vectors(text).position_km)
            actual = getattr(result.position_km, body)[i]
            comparisons.append(
                {
                    "utc": utc,
                    "body": body,
                    "vector_error_km": math.dist(actual, vectors[body]),
                    "header": facts,
                }
            )
        for pair, a, b in (
            ("earth_moon", "earth", "moon"),
            ("sun_earth", "sun", "earth"),
            ("sun_moon", "sun", "moon"),
        ):
            expected = math.dist(vectors[a], vectors[b])
            actual = getattr(result.distance_km, pair)[i]
            comparisons.append(
                {
                    "utc": utc,
                    "pair": pair,
                    "reference_km": expected,
                    "computed_km": actual,
                    "distance_error_km": abs(actual - expected),
                }
            )
    errors = [
        float(str(row.get("vector_error_km", row.get("distance_error_km")))) for row in comparisons
    ]
    report = {
        "profile": profile.profile_id,
        "kernel_sha256": list(profile.sha256),
        "frame": "J2000 / Horizons ICRF",
        "origin": "SUN",
        "correction": "NONE",
        "threshold_km": THRESHOLD_KM,
        "threshold_status": "engineering check, not ASTRO approval",
        "max_error_km": max(errors),
        "passed": max(errors) <= THRESHOLD_KM,
        "comparisons": comparisons,
    }
    (REFERENCE / "comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"E10A Horizons: {len(comparisons)} checks; max error {max(errors):.9f} km")
    if not report["passed"]:
        raise SystemExit("Horizons discrepancy exceeds the engineering threshold")


if __name__ == "__main__":
    main()
