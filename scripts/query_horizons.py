"""Interoghează JPL Horizons pentru cazurile din data/reference/horizons/cases.json și arhivează
răspunsurile originale.

Rulare din rădăcina repository-ului (cere rețea; kernelurile sunt necesare numai pentru conversia
UTC → TDB a cererilor de vectori):
    backend\\.venv\\Scripts\\python scripts\\query_horizons.py             (numai ce lipsește)
    backend\\.venv\\Scripts\\python scripts\\query_horizons.py --refresh   (reinterogare completă)

Pentru fiecare cerere se scriu, în data/reference/horizons/<case_id>/:
    <corp>_<tip>.response.json   corpul răspunsului, octet cu octet, nemodificat
    <corp>_<tip>.request.json    URL-ul, parametrii, momentul accesării, statusul HTTP, SHA-256
Un răspuns cu eroare sau fără tabel nu se arhivează ca referință: se salvează ca .error.json, iar
scriptul se termină cu cod 1.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.astro import horizons  # noqa: E402
from lunarhorizon.astro.bodies import ObserverSite  # noqa: E402
from lunarhorizon.astro.kernels import load_profile  # noqa: E402
from lunarhorizon.astro.timeconv import et_to_tdb_calendar, utc_to_et  # noqa: E402
from lunarhorizon.contracts.export import dumps  # noqa: E402
from lunarhorizon.core.utc import format_utc, parse_utc  # noqa: E402

REFERENCE_DIR = ROOT / "data" / "reference" / "horizons"
PAUSE_BETWEEN_REQUESTS_S = 1.0


def _utc_calendar(utc: str) -> str:
    moment = parse_utc(utc)
    return f"{moment:%Y-%m-%d %H:%M:%S}.{moment.microsecond // 1000:03d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Arhivează referințe JPL Horizons.")
    parser.add_argument(
        "--refresh", action="store_true", help="reinterogare și pentru cele existente"
    )
    args = parser.parse_args()

    cases = json.loads((REFERENCE_DIR / "cases.json").read_text(encoding="utf-8"))["cases"]
    profile = None
    failures = 0
    for case in cases:
        site = ObserverSite(
            case["latitude_deg"],
            case["longitude_deg"],
            case["surface_height_m"],
            case["observer_height_m"],
        )
        case_dir = REFERENCE_DIR / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        for kind in case["queries"]:
            for body in ("sun", "earth"):
                stem = f"{body}_{kind}"
                if (case_dir / f"{stem}.response.json").exists() and not args.refresh:
                    print(f"există: {case['case_id']}/{stem}")
                    continue
                time_input: dict[str, str] = {"utc": case["utc"]}
                if kind == "observer":
                    params = horizons.observer_params(site, body, _utc_calendar(case["utc"]))
                else:
                    profile = profile or load_profile()
                    tdb = et_to_tdb_calendar(utc_to_et(case["utc"], profile), profile)
                    time_input["tdb_calendar"] = tdb
                    time_input["tdb_from"] = f"SPICE str2et/timout, profil {profile.profile_id}"
                    params = horizons.vector_params(site, body, tdb)
                url = horizons.build_url(params)
                retrieved = format_utc(datetime.now(UTC))
                status, raw = horizons.fetch(url)
                record = {
                    "case_id": case["case_id"],
                    "body": body,
                    "kind": kind,
                    "url": url,
                    "params": params,
                    "time_input": time_input,
                    "retrieved_at_utc": retrieved,
                    "http_status": status,
                    "response_file": f"{stem}.response.json",
                    "response_bytes": len(raw),
                    "response_sha256": hashlib.sha256(raw).hexdigest(),
                }
                try:
                    text = horizons.result_text(raw)
                    if kind == "observer":
                        horizons.parse_observer(text)
                    else:
                        horizons.parse_vectors(text)
                except (horizons.HorizonsError, ValueError, StopIteration) as exc:
                    failures += 1
                    (case_dir / f"{stem}.error.json").write_bytes(raw)
                    print(f"EȘEC {case['case_id']}/{stem}: {exc}")
                    continue
                (case_dir / f"{stem}.response.json").write_bytes(raw)
                (case_dir / f"{stem}.request.json").write_text(
                    dumps(record), encoding="utf-8", newline="\n"
                )
                print(f"arhivat: {case['case_id']}/{stem} (HTTP {status}, {len(raw)} octeți)")
                time.sleep(PAUSE_BETWEEN_REQUESTS_S)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
