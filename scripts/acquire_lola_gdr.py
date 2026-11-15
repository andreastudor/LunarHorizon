"""Achiziția nivelului de teren îndepărtat pentru orizont (E09): produse polare LOLA GDR (PDS3).

Descarcă eticheta `.LBL` și imaginea `.IMG` din `LRO-L-LOLA-4-GDR-V1.0` în `data/_raw/lola_gdr/`
(neversionat), verifică dimensiunea față de etichetă și față de `Content-Length`, calculează
SHA-256 (PDS nu publică sume de control pentru aceste fișiere: integritatea la sursă NU este
verificată, numai dimensiunea) și scrie:

- `data/manifests/lola_gdr_acquisition.json` — sumele fixate (blocare);
- intrarea produsului, cu `role = "far"`, în `data/manifests/terrain_products.json`.

Utilizare (din rădăcină): `backend\\.venv\\Scripts\\python scripts\\acquire_lola_gdr.py
LDEM_75S_120M [--verify] [--no-register] [--skip-download]`. Cu `--verify` nu descarcă;
recalculează SHA-256 și compară cu blocarea.
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.contracts.manifests import DemProductManifest  # noqa: E402
from lunarhorizon.terrain.lola_gdr import load_lola_polar_grid, read_label  # noqa: E402

LANDING = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/"
)
CITATION = (
    "Smith, D.E., et al., LRO LOLA Gridded Data Records, LRO-L-LOLA-4-GDR-V1.0, NASA Planetary "
    "Data System (PDS Geosciences Node)"
)
RAW_DIR = ROOT / "data" / "_raw" / "lola_gdr"
LOCK = ROOT / "data" / "manifests" / "lola_gdr_acquisition.json"
PRODUCTS = ROOT / "data" / "manifests" / "terrain_products.json"
CHUNK = 1 << 20


def product_id(name: str) -> str:
    return f"lola_gdr_{name.lower()}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "LunarHorizon-data-acquisition"})
    with urllib.request.urlopen(request, timeout=120) as response:
        expected = int(response.headers.get("Content-Length", "-1"))
        partial = target.with_suffix(target.suffix + ".part")
        written = 0
        with partial.open("wb") as handle:
            while block := response.read(CHUNK):
                handle.write(block)
                written += len(block)
    if expected >= 0 and written != expected:
        partial.unlink()
        raise RuntimeError(f"{target.name}: {written} octeți primiți, Content-Length {expected}")
    partial.replace(target)
    return written


def product_entry(name: str, label_sha: str, image_sha: str, image_size: int) -> dict[str, object]:
    label = read_label(RAW_DIR / f"{name}.LBL")
    return {
        "product_id": product_id(name),
        "title": f"LOLA GDR polar {name} (PDS3, {label.map_scale_m:g} m/pixel)",
        "institution": "NASA GSFC / PDS Geosciences Node",
        "landing_page_url": LANDING,
        "citation": CITATION,
        "accessed_at": datetime.now(tz=UTC).date().isoformat(),
        "role": "far",
        "resolution_m": label.map_scale_m,
        "frame_id": "MOON_ME_DE421",
        "metadata_origin": "read_from_file",
        "crs_wkt": None,
        "reference_radius_m": label.offset_m,
        "vertical_units": "m",
        "vertical_reference": (
            f"PDS label: HEIGHT = DN * {label.scaling_factor:g} relative to OFFSET "
            f"{label.offset_m:.0f} m sphere ({label.coordinate_system_name})"
        ),
        "nodata_value": None,
        "gap_handling": (
            "Grid without declared NoData (interpolated where LOLA tracks are missing); "
            "declared frame MEAN EARTH/POLAR AXIS OF DE421"
        ),
        "min_latitude_deg": -90.0,
        "max_latitude_deg": label.maximum_latitude_deg,
        "files": [
            {
                "kind": "height",
                "filename": f"{name}.IMG",
                "url": f"{LANDING}{name.lower()}.img",
                "sha256": image_sha,
                "size_bytes": image_size,
            },
            {
                "kind": "label",
                "filename": f"{name}.LBL",
                "url": f"{LANDING}{name.lower()}.lbl",
                "sha256": label_sha,
                "size_bytes": (RAW_DIR / f"{name}.LBL").stat().st_size,
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Achiziția produselor polare LOLA GDR (E09).")
    parser.add_argument("names", nargs="+", help="de exemplu LDEM_75S_120M")
    parser.add_argument("--verify", action="store_true", help="numai verificarea sumelor fixate")
    parser.add_argument("--no-register", action="store_true", help="nu scrie terrain_products")
    parser.add_argument(
        "--skip-download", action="store_true", help="folosește fișierele deja descărcate"
    )
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.is_file() else {"files": {}}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in args.names:
        label_path, image_path = RAW_DIR / f"{name}.LBL", RAW_DIR / f"{name}.IMG"
        if args.verify:
            for path in (label_path, image_path):
                expected = lock["files"].get(path.name, {}).get("sha256")
                actual = sha256_of(path) if path.is_file() else None
                ok = expected is not None and actual == expected
                failures += not ok
                print(f"{path.name}: {'OK' if ok else 'NEPOTRIVIRE sau lipsă'}")
            continue
        if not args.skip_download:
            download(f"{LANDING}{name.lower()}.lbl", label_path)
            download(f"{LANDING}{name.lower()}.img", image_path)
        # Eticheta și dimensiunea fișierului trebuie să corespundă (altfel eroare).
        load_lola_polar_grid(label_path, image_path, product_id(name), None)
        size = image_path.stat().st_size
        label_sha, image_sha = sha256_of(label_path), sha256_of(image_path)
        for path, digest in ((label_path, label_sha), (image_path, image_sha)):
            lock["files"][path.name] = {
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "source_checksum": "none published by PDS; size checked against label and HTTP",
            }
        print(f"{name}: {size} octeți, SHA-256 {image_sha}")
        if not args.no_register:
            document = json.loads(PRODUCTS.read_text(encoding="utf-8"))
            entries = [p for p in document["products"] if p["product_id"] != product_id(name)]
            entries.append(product_entry(name, label_sha, image_sha, size))
            document["products"] = entries
            DemProductManifest.model_validate(document)
            PRODUCTS.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    if not args.verify:
        lock["source"] = LANDING
        LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
