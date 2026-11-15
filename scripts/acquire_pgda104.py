"""Selective acquisition of the PGDA 104 elevation rasters (one GeoTIFF member per archive).

Only the `*_GLDELEV_005.tif` member of each Zenodo ZIP is read, through HTTP byte ranges; the full
archives (1-4.4 GB each) are not downloaded. The ZIP member CRC is verified by `zipfile`; the
SHA-256 of each extracted member is pinned in `data/manifests/pgda104_acquisition.json` at the first
acquisition and verified afterwards. The provider's MD5 covers whole archives and is NOT verified.

Usage (from the repository root):
  backend\\.venv\\Scripts\\python scripts\\acquire_pgda104.py --list
  backend\\.venv\\Scripts\\python scripts\\acquire_pgda104.py --all          # missing members only
  backend\\.venv\\Scripts\\python scripts\\acquire_pgda104.py --region haworth
  backend\\.venv\\Scripts\\python scripts\\acquire_pgda104.py --verify
"""

import argparse
import hashlib
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from download_terrain import RangeReader

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data/catalog/pgda104_extent_check.json"
LOCK = ROOT / "data/manifests/pgda104_acquisition.json"
RAW = ROOT / "data/_raw/pgda104"
RECORD = "https://zenodo.org/records/17954508/files"


def slug(archive: str) -> str:
    """'A3CLR22_10_Leibnitz_Beta_Plateau.zip' → 'leibnitz_beta_plateau'."""
    name = re.sub(r"^A3CLR22_\d+_", "", archive.removesuffix(".zip"))
    return name.lower()


def regions() -> list[dict[str, object]]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    result = []
    for archive in inventory["archives"]:
        result.append(
            {
                "slug": slug(str(archive["archive"])),
                "archive": archive["archive"],
                "url": f"{RECORD}/{archive['archive']}?download=1",
                "archive_size_bytes": archive["size_bytes"],
                "archive_md5_published": archive["md5"],
                "member": archive["raster"],
                "member_size_bytes": archive["raster_size"],
                "bounds_m": archive["bounds_m"],
                "width": archive["width"],
                "height": archive["height"],
            }
        )
    return sorted(result, key=lambda r: str(r["slug"]))


def raw_path(region: dict[str, object]) -> Path:
    return RAW / Path(str(region["member"])).name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_lock() -> dict[str, dict[str, object]]:
    if not LOCK.is_file():
        return {}
    data: dict[str, dict[str, object]] = json.loads(LOCK.read_text(encoding="utf-8"))["members"]
    return data


def write_lock(members: dict[str, dict[str, object]]) -> None:
    document = {
        "schema": "pgda104-acquisition-v1",
        "note": (
            "SHA-256 computed by LunarHorizon at first acquisition (not published by the "
            "provider); ZIP member CRC verified by zipfile; whole-archive MD5 not verified."
        ),
        "members": dict(sorted(members.items())),
    }
    LOCK.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def acquire(region: dict[str, object], members: dict[str, dict[str, object]]) -> None:
    path = raw_path(region)
    key = str(region["slug"])
    if path.is_file():
        print(f"{key}: present ({path.stat().st_size} bytes)")
    else:
        started = time.monotonic()
        reader = RangeReader(str(region["url"]), int(str(region["archive_size_bytes"])))
        with zipfile.ZipFile(reader) as archive:
            data = archive.read(str(region["member"]))  # CRC verified by zipfile
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        seconds = time.monotonic() - started
        print(f"{key}: downloaded {len(data)} bytes in {seconds:.1f} s", flush=True)
    digest = sha256(path)
    pinned = members.get(key)
    if pinned is None:
        members[key] = {
            "member": region["member"],
            "sha256": digest,
            "size_bytes": path.stat().st_size,
            "retrieved_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "archive": region["archive"],
            "archive_md5_published_not_verified": region["archive_md5_published"],
        }
    elif pinned["sha256"] != digest:
        raise ValueError(f"{key}: SHA-256 {digest} differs from the pinned value")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--all", action="store_true")
    group.add_argument("--region")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    all_regions = regions()
    if args.list:
        for region in all_regions:
            state = "present" if raw_path(region).is_file() else "missing"
            print(f"{region['slug']:32} {region['member_size_bytes']:>10} bytes  {state}")
        return
    members = read_lock()
    if args.verify:
        for region in all_regions:
            if raw_path(region).is_file():
                acquire(region, members)
        print("verified")
        return
    selected = all_regions if args.all else [r for r in all_regions if r["slug"] == args.region]
    if not selected:
        raise SystemExit(f"unknown region {args.region!r}")
    for region in selected:
        try:
            acquire(region, members)
        except Exception as error:  # access problems are recorded; the others continue
            print(f"{region['slug']}: FAILED {type(error).__name__}: {error}", flush=True)
        write_lock(members)


if __name__ == "__main__":
    main()
