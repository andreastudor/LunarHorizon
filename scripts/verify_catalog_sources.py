"""Reverifică pozițiile din data/catalog/sites.json la sursele originale (cere rețea).

Rulare din rădăcina repository-ului, cu Python-ul mediului virtual al backendului:
    backend\\.venv\\Scripts\\python scripts\\verify_catalog_sources.py [--write-report]

Pentru fiecare intrare:
  1. produsul PDS LROC (ANTHROPOGENIC_OBJECTS_180.ZIP) se descarcă în data/_raw/ (exclus din Git),
     SHA-256-ul trebuie să fie cel din catalog, iar înregistrarea OBJECT_ID trebuie să aibă
     LATITUDE, LONGITUDE, UNCERTAIN și RADIUS (altitudinea) egale cu cele din catalog;
  2. fiecare sursă HTML deschisă (pagini LROC, NASA, ISRO) se descarcă, iar citatul din catalog
     trebuie să apară în textul paginii (după eliminarea etichetelor și normalizarea spațiilor);
  3. sursele PDF (kituri de presă NASA) NU se verifică automat: se raportează ca „manual”.

O verificare reușită înseamnă că documentul original conține încă valorile din catalog. Nu înseamnă
că poziția este corectă fizic sau că sursa este mai bună decât altele. Orice sursă inaccesibilă este
raportată ca atare și face scriptul să se termine cu cod 1.
"""

import argparse
import hashlib
import html
import re
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.catalog import DEFAULT_CATALOG_PATH, load_catalog  # noqa: E402
from lunarhorizon.contracts.catalog import Site, SourceRecord  # noqa: E402
from lunarhorizon.contracts.export import dumps  # noqa: E402
from lunarhorizon.core.conventions import REFERENCE_RADIUS_M  # noqa: E402

RAW_DIR = ROOT / "data" / "_raw" / "catalog_sources"
REPORT_PATH = ROOT / "data" / "catalog" / "source_verification.json"
PDS_ZIP_URL = (
    "https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/SHAPEFILE/"
    "ANTHROPOGENIC_OBJECTS/ANTHROPOGENIC_OBJECTS_180.ZIP"
)
USER_AGENT = "Mozilla/5.0 LunarHorizon-catalog-source-check"
# Valorile se compară ca numere, nu ca texte.
COORD_TOLERANCE = 1e-9
RADIUS_TOLERANCE_M = 1e-3
TABLE_QUOTE_SUFFIX = " (Mean Observed"


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return bytes(response.read())


def _page_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def _read_dbf(data: bytes) -> list[dict[str, Any]]:
    count, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields: list[tuple[str, str, int]] = []
    offset = 32
    while data[offset] != 0x0D:
        name = data[offset : offset + 11].split(b"\0")[0].decode("ascii")
        fields.append((name, chr(data[offset + 11]), data[offset + 16]))
        offset += 32
    rows: list[dict[str, Any]] = []
    for index in range(count):
        record = data[header_len + index * record_len : header_len + (index + 1) * record_len]
        if record[:1] == b"*":
            continue
        position, row = 1, {}
        for name, kind, length in fields:
            raw = record[position : position + length].decode("utf-8", errors="replace").strip()
            position += length
            row[name] = float(raw) if kind in "NF" and raw else raw
        rows.append(row)
    return rows


def _object_id(source: SourceRecord) -> str | None:
    match = re.search(r"OBJECT_ID=([A-Za-z0-9_]+)", source.identifier or "")
    return match.group(1) if match else None


def _check_pds(
    site: Site, source: SourceRecord, records: dict[str, dict[str, Any]], zip_sha: str
) -> dict[str, Any]:
    oid = _object_id(source)
    checks: dict[str, str] = {}
    result: dict[str, Any] = {"kind": "pds_product", "object_id": oid, "checks": checks}
    if source.file_sha256 != zip_sha:
        checks["zip_sha256"] = f"catalog {source.file_sha256} != descărcat {zip_sha}"
    record = records.get(oid or "")
    if record is None or source.coordinates is None:
        checks["record"] = "înregistrare lipsă în produs"
        return result
    nan = float("nan")
    expected_elevation = float(record["RADIUS"]) - REFERENCE_RADIUS_M
    pairs = {
        "latitude": (source.coordinates.latitude_deg, float(record["LATITUDE"]), COORD_TOLERANCE),
        "longitude": (
            source.coordinates.longitude_deg,
            float(record["LONGITUDE"]),
            COORD_TOLERANCE,
        ),
        "uncertainty_m": (
            nan if source.published_uncertainty_m is None else source.published_uncertainty_m,
            float(record["UNCERTAIN"]),
            COORD_TOLERANCE,
        ),
        "elevation_m": (
            nan if site.elevation_m is None else site.elevation_m,
            expected_elevation,
            RADIUS_TOLERANCE_M,
        ),
    }
    for name, (catalog_value, original, tolerance) in pairs.items():
        if not abs(catalog_value - original) <= tolerance:
            checks[name] = f"catalog {catalog_value} != produs {original}"
    return result


def _check_html(source: SourceRecord, cache: dict[str, str]) -> dict[str, Any]:
    checks: dict[str, str] = {}
    result: dict[str, Any] = {"kind": "html_quote", "url": source.url, "checks": checks}
    try:
        if source.url not in cache:
            cache[source.url] = _page_text(_fetch(source.url))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        result["inaccessible"] = str(exc)
        return result
    quote = re.sub(r"\s+", " ", (source.quote or "").split(TABLE_QUOTE_SUFFIX)[0]).strip()
    if not quote or quote not in cache[source.url]:
        checks["quote"] = "citatul nu apare în textul paginii"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Reverifică catalogul la sursele originale.")
    parser.add_argument("--write-report", action="store_true", help=f"scrie {REPORT_PATH.name}")
    args = parser.parse_args()

    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "ANTHROPOGENIC_OBJECTS_180.ZIP"
    records: dict[str, dict[str, Any]] = {}
    zip_sha = ""
    pds_error: str | None = None
    try:
        zip_path.write_bytes(_fetch(PDS_ZIP_URL))
        zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        with zipfile.ZipFile(zip_path) as archive:
            rows = _read_dbf(archive.read("ANTHROPOGENIC_OBJECTS_180.DBF"))
        records = {str(row["OBJECT_ID"]): row for row in rows}
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, zipfile.BadZipFile) as exc:
        pds_error = str(exc)

    page_cache: dict[str, str] = {}
    report: list[dict[str, Any]] = []
    failures = inaccessible = manual = 0
    for site in catalog.sites:
        entry: dict[str, Any] = {"site_id": site.id, "sources": []}
        for source in site.position_sources:
            if source.access != "opened_original":
                entry["sources"].append({"kind": "not_accessible", "url": source.url})
                continue
            if source.url.lower().endswith(".pdf"):
                manual += 1
                entry["sources"].append({"kind": "pdf_manual", "url": source.url})
                continue
            if _object_id(source) is not None:
                result = (
                    {"kind": "pds_product", "inaccessible": pds_error}
                    if pds_error
                    else _check_pds(site, source, records, zip_sha)
                )
            else:
                result = _check_html(source, page_cache)
            if "inaccessible" in result:
                inaccessible += 1
            elif result["checks"]:
                failures += 1
            entry["sources"].append(result)
        report.append(entry)

    for entry in report:
        for result in entry["sources"]:
            if "inaccessible" in result:
                state = f"INACCESIBIL ({result['inaccessible']})"
            elif result.get("checks"):
                state = f"EȘEC {result['checks']}"
            elif result["kind"] in ("pdf_manual", "not_accessible"):
                state = "manual / neaccesat"
            else:
                state = "ok"
            print(f"{entry['site_id']:30s} {result['kind']:14s} {state}")

    summary = {"failures": failures, "inaccessible": inaccessible, "manual_pdf_sources": manual}
    print(f"\nRezumat: {summary}")
    if args.write_report:
        document = {
            "description": (
                "Reverificarea pozițiilor din catalog la sursele originale. Valorile din catalog "
                "coincid cu documentele deschise la rulare; nu dovedesc acuratețea fizică."
            ),
            "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "catalog_version": catalog.catalog_version,
            "pds_zip_sha256": zip_sha or None,
            "summary": summary,
            "results": report,
        }
        REPORT_PATH.write_text(dumps(document), encoding="utf-8", newline="\n")
        print(f"scris: {REPORT_PATH.relative_to(ROOT)}")
    return 1 if (failures or inaccessible) else 0


if __name__ == "__main__":
    sys.exit(main())
