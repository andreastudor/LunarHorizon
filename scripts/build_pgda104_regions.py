"""Build terrain products, the terrain index and the catalog region points for all PGDA 104 regions.

For every region whose elevation member was acquired (scripts/acquire_pgda104.py), with the same
method as E05 (scripts/build_terrain.py, kept unchanged for Leibnitz Beta):
  - `calculation.tif`: an identical copy of the official GeoTIFF (5 m/pixel), used for calculations;
  - visual levels: block means over factors 8 and the first of 16/20/24/40 dividing the raster size,
    a block with any NoData stays NoData (never zero);
  - `terrain_manifest.json` (contract TerrainManifest) and its versioned copy;
  - the representative point: the raster centre pixel (row = height // 2, column = width // 2) — a
    method chosen by LunarHorizon, not a landing site and not a published coordinate.
It also writes `data/manifests/terrain_index.json` (all 13 regions, acquired or not), adds the
products
to `data/manifests/terrain_products.json` and regenerates the `pgda104_*_point` entries of the site
catalog. Leibnitz Beta keeps its E05 identifiers (terrain `leibnitz_beta_provisional`).

Usage: backend\\.venv\\Scripts\\python scripts\\build_pgda104_regions.py [--catalog-only]
"""

import argparse
import hashlib
import json
import shutil
import sys
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from acquire_pgda104 import RAW, read_lock, regions
from rasterio.transform import Affine
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from lunarhorizon.catalog import DEFAULT_CATALOG_PATH  # noqa: E402
from lunarhorizon.contracts.catalog import Catalog  # noqa: E402
from lunarhorizon.contracts.manifests import DemProductManifest, TerrainManifest  # noqa: E402

CACHE = ROOT / "data/_cache/terrain"
MANIFESTS = ROOT / "data/manifests/terrain"
INDEX = ROOT / "data/manifests/terrain_index.json"
PRODUCTS = ROOT / "data/manifests/terrain_products.json"
CITATION = "Bertone et al., Enhanced Topography Models, doi:10.3847/PSJ/ae5b70"
LANDING = "https://pgda.gsfc.nasa.gov/products/104"
LONGLAT = "+proj=longlat +R=1737400 +no_defs"
FRAME = "MOON_ME_DE421"
ACCESSED = "2026-11-15"
# Leibnitz Beta: products and identifiers from E05/E08, built by scripts/build_terrain.py.
LEIBNITZ = {
    "terrain_id": "leibnitz_beta_provisional",
    "product_id": "pgda104_leibnitz_beta",
    "manifest": "data/manifests/leibnitz_terrain.json",
    "cache_dir": "data/_cache/terrain/leibnitz_beta",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def region_name(archive: str) -> str:
    """'A3CLR22_12_deGerlache_Kocher_Massif.zip' → 'deGerlache Kocher Massif' (archive spelling)."""
    parts = archive.removesuffix(".zip").split("_")[2:]
    return " ".join(parts)


def identifiers(slug: str) -> dict[str, str]:
    if slug == "leibnitz_beta_plateau":
        return dict(LEIBNITZ)
    return {
        "terrain_id": f"{slug}_provisional",
        "product_id": f"pgda104_{slug}",
        "manifest": f"data/manifests/terrain/{slug}.json",
        "cache_dir": f"data/_cache/terrain/{slug}",
    }


def second_factor(size: int) -> int:
    for factor in (16, 20, 24, 40):
        if size % factor == 0:
            return factor
    raise ValueError(f"no visual factor divides {size}")


def footprint(ds: Any) -> list[list[float]]:
    b = ds.bounds
    corners = [(b.left, b.bottom), (b.right, b.bottom), (b.right, b.top), (b.left, b.top)]
    xs: list[float] = []
    ys: list[float] = []
    for start, end in pairwise([*corners, corners[0]]):
        for step in range(16):
            xs.append(start[0] + (end[0] - start[0]) * step / 16)
            ys.append(start[1] + (end[1] - start[1]) * step / 16)
    xs.append(xs[0])
    ys.append(ys[0])
    lons, lats = transform(ds.crs, LONGLAT, xs, ys)
    return [[float(lon), float(lat)] for lon, lat in zip(lons, lats, strict=True)]


def build_region(region: dict[str, Any], ids: dict[str, str], pinned_sha: str) -> dict[str, Any]:
    source = RAW / Path(str(region["member"])).name
    if sha256(source) != pinned_sha:
        raise ValueError(f"{region['slug']}: source differs from the pinned SHA-256")
    out = ROOT / ids["cache_dir"]
    out.mkdir(parents=True, exist_ok=True)
    calc = out / "calculation.tif"
    if not calc.is_file() or sha256(calc) != pinned_sha:
        shutil.copyfile(source, calc)
    with rasterio.open(calc) as ds:
        if ds.crs is None or ds.count != 1 or ds.width != ds.height:
            raise ValueError(f"{region['slug']}: incompatible raster")
        if [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top] != region["bounds_m"]:
            raise ValueError(f"{region['slug']}: bounds differ from the inventory")
        data = ds.read(1, masked=True)
        invalid = np.ma.getmaskarray(data) | ~np.isfinite(data.data)
        lods = []
        for level, factor in enumerate((8, second_factor(ds.width))):
            height, width = ds.height // factor, ds.width // factor
            valid = (~invalid).reshape(height, factor, width, factor).all(axis=(1, 3))
            safe = np.where(invalid, 0, data.data).astype(np.float64)
            mean = safe.reshape(height, factor, width, factor).mean(axis=(1, 3))
            visual = np.where(valid, mean, np.nan).astype("float32")
            name = f"visual_{factor}.tif"
            with rasterio.open(
                out / name,
                "w",
                driver="GTiff",
                width=width,
                height=height,
                count=1,
                dtype="float32",
                crs=ds.crs,
                nodata=float("nan"),
                transform=ds.transform @ Affine.scale(factor),
                compress="deflate",
            ) as dst:
                dst.write(visual, 1)
            lods.append(
                {
                    "level": level,
                    "visual_resolution_m": ds.res[0] * factor,
                    "width_px": width,
                    "height_px": height,
                    "heights_path": name,
                    "encoding": "GeoTIFF float32; NaN = NoData; any NoData in a block → NoData",
                    "sha256": sha256(out / name),
                }
            )
        row, col = ds.height // 2, ds.width // 2
        if invalid[row, col]:
            raise ValueError(f"{region['slug']}: centre pixel is NoData; no point proposed")
        x, y = ds.xy(row, col)
        lon, lat = transform(ds.crs, LONGLAT, [x], [y])
        manifest = {
            "schema_version": "0.6.0",
            "terrain_id": ids["terrain_id"],
            "source": {
                "product_id": ids["product_id"],
                "url": region["url"],
                "sha256": pinned_sha,
                "citation": CITATION,
            },
            "frame_id": FRAME,
            "crs": {"proj4": None, "wkt": ds.crs.to_wkt()},
            "reference_radius_m": 1737400.0,
            "vertical": {
                "units": "m",
                "reference": "Sphere of 1737400 m (product README)",
                "exaggeration_default_factor": 1,
            },
            "calc_resolution_m": float(ds.res[0]),
            "local_origin": {
                "latitude_deg": float(lat[0]),
                "longitude_deg": float(lon[0]),
                "elevation_m": float(data.data[row, col]),
            },
            "bounds": {
                "x_min_m": ds.bounds.left,
                "x_max_m": ds.bounds.right,
                "y_min_m": ds.bounds.bottom,
                "y_max_m": ds.bounds.top,
            },
            "nodata": {
                "present": bool(invalid.any()),
                "encoding": str(ds.nodata),
                "area_fraction": float(invalid.mean()),
            },
            "interpolated_pixels": {
                "flagged": False,
                "note": (
                    "SfS model; LROC contribution not inspected. "
                    "MOON_ME_DE421 is an unconfirmed hypothesis."
                ),
            },
            "lods": lods,
        }
        ring = footprint(ds)
    raw = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    TerrainManifest.model_validate_json(raw)
    (out / "terrain_manifest.json").write_text(raw, encoding="utf-8")
    versioned = ROOT / ids["manifest"]
    versioned.parent.mkdir(parents=True, exist_ok=True)
    versioned.write_text(raw, encoding="utf-8")
    return {
        "manifest": manifest,
        "centre": {"row": row, "column": col},
        "ring": ring,
        "nodata_fraction": float(invalid.mean()),
    }


def catalog_entry(region: dict[str, Any], built: dict[str, Any], pinned_sha: str) -> dict[str, Any]:
    manifest = built["manifest"]
    origin = manifest["local_origin"]
    name = region_name(str(region["archive"]))
    url = str(region["url"])
    member = Path(str(region["member"])).name
    coordinates = {
        "latitude_deg": origin["latitude_deg"],
        "longitude_deg": origin["longitude_deg"],
        "frame_description": (
            "Moon (2015) - Sphere / Ocentric, south polar stereographic (IAU 30135), "
            "R = 1 737 400 m; geographic coordinates of the pixel centre computed by LunarHorizon"
        ),
        "note": (
            f"Centre pixel row {built['centre']['row']}, column {built['centre']['column']} "
            f"of {member}"
        ),
    }
    return {
        "id": f"pgda104_{region['slug']}_point",
        "name": f"{name} — DEM representative point (PGDA 104 raster centre)",
        "mission": None,
        "agency": None,
        "operator": None,
        "country": None,
        "status": "dem_region",
        "mission_status": "not_applicable",
        "geometry_type": "region",
        "position_kind": "representative_point",
        "latitude_deg": origin["latitude_deg"],
        "longitude_deg": origin["longitude_deg"],
        "frame_id": FRAME,
        "original_coordinates": coordinates,
        "horizontal_uncertainty_m": None,
        "elevation_m": origin["elevation_m"],
        "elevation_reference": (
            "Height above the 1 737 400 m sphere, value of the GeoTIFF pixel (PGDA 104 README)"
        ),
        "region": {"type": "Polygon", "coordinates": [built["ring"]]},
        "landing_date_utc": None,
        "related_site_id": None,
        "planned_target_note": None,
        "source_url": url,
        "accessed_at": ACCESSED,
        "position_sources": [
            {
                "used_for": "position",
                "institution": "NASA GSFC Planetary Geodesy Data Archive (PGDA 104), Zenodo",
                "title": f"{region['archive']} — {member}",
                "url": url,
                "identifier": "doi:10.5281/zenodo.17954508",
                "version_or_update": None,
                "published": None,
                "accessed_at": ACCESSED,
                "locator": (
                    f"{member}: raster centre pixel (row {built['centre']['row']}, column "
                    f"{built['centre']['column']}); method chosen by LunarHorizon"
                ),
                "access": "opened_original",
                "coordinates": coordinates,
                "declared_frame": "Moon (2015) - Sphere / Ocentric (IAU 30100), CRS of the GeoTIFF",
                "frame_realization_stated": False,
                "published_uncertainty_m": None,
                "uncertainty_definition": None,
                "quote": None,
                "file_sha256": pinned_sha,
            }
        ],
        "position_verification": "verified_at_original",
        "adoption_note": (
            "Punct reprezentativ DEM: pixelul central al rasterului GLDELEV (metodă LunarHorizon), "
            "nu centrul oficial al regiunii, nu loc de aterizare, nu țintă și nu selecție curentă. "
            "IPOTEZĂ: cadrul MOON_ME_DE421 declarat pentru produsele PGDA (D-10 deschisă); "
            "nicio conversie de cadru."
        ),
        "description_ro": None,
        "description_en": (
            f"DEM representative point: the centre pixel of the PGDA 104 raster named {name}, "
            "chosen by LunarHorizon. It is not the official centre of the region, not a landing "
            "site, not an approved landing candidate and not a current mission selection."
        ),
        "terrain_available": True,
    }


def product_entry(region: dict[str, Any], ids: dict[str, str], pinned_sha: str) -> dict[str, Any]:
    member = Path(str(region["member"])).name
    return {
        "product_id": ids["product_id"],
        "title": f"PGDA 104 {region_name(str(region['archive']))} SDEM (provisional)",
        "institution": "NASA GSFC",
        "landing_page_url": LANDING,
        "citation": CITATION,
        "accessed_at": ACCESSED,
        "role": "near",
        "resolution_m": 5.0,
        "frame_id": FRAME,
        "metadata_origin": "read_from_file",
        "crs_wkt": None,
        "reference_radius_m": 1737400.0,
        "vertical_units": "m",
        "vertical_reference": "README ZIP: height relative to 1737400 m sphere",
        "nodata_value": -3.4028234663852886e38,
        "gap_handling": (
            "SfS interpolated; image mask not inspected; DE421 frame is an unconfirmed hypothesis"
        ),
        "min_latitude_deg": None,
        "max_latitude_deg": None,
        "files": [
            {
                "kind": "height",
                "filename": member,
                "url": str(region["url"]),
                "sha256": pinned_sha,
                "size_bytes": int(region["member_size_bytes"]),
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    lock = read_lock()
    index_entries = []
    built_regions: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {}
    for region in regions():
        slug = str(region["slug"])
        ids = identifiers(slug)
        pinned = lock.get(slug)
        entry = {
            "slug": slug,
            "region_name": region_name(str(region["archive"])),
            **ids,
            "archive": region["archive"],
            "member": region["member"],
            "member_size_bytes": region["member_size_bytes"],
            "bounds_m": region["bounds_m"],
            "calc_resolution_m": 5.0,
            "frame_id": FRAME,
            "acquired": pinned is not None,
        }
        if pinned is None:
            entry["manifest"] = None
            print(f"{slug}: not acquired; listed as not downloaded")
        elif slug == "leibnitz_beta_plateau":
            manifest = json.loads((ROOT / ids["manifest"]).read_text(encoding="utf-8"))
            with rasterio.open(ROOT / ids["cache_dir"] / "calculation.tif") as ds:
                ring = footprint(ds)
            built_regions[slug] = (
                region,
                {
                    "manifest": manifest,
                    "centre": {"row": 1600, "column": 1600},
                    "ring": ring,
                    "nodata_fraction": manifest["nodata"]["area_fraction"],
                },
                str(pinned["sha256"]),
            )
            print(f"{slug}: E05 products reused")
        else:
            built = build_region(region, ids, str(pinned["sha256"]))
            built_regions[slug] = (region, built, str(pinned["sha256"]))
            print(f"{slug}: built ({built['nodata_fraction']:.4%} NoData)")
        index_entries.append(entry)

    INDEX.write_text(
        json.dumps(
            {
                "schema": "terrain-index-v1",
                "selection_rule": (
                    "Among the indexed products whose raster rectangle contains the point and "
                    "whose "
                    "frame equals the requested frame: prefer a valid (not NoData, not edge) "
                    "calculation sample, then the finer calculation resolution, then the larger "
                    "distance to the raster edge, then the smaller terrain_id. Rasters are never "
                    "combined."
                ),
                "entries": index_entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    keep = [p for p in products["products"] if p["product_id"] == LEIBNITZ["product_id"]]
    for slug, (region, _built, sha) in sorted(built_regions.items()):
        if slug != "leibnitz_beta_plateau":
            keep.append(product_entry(region, identifiers(slug), sha))
    products["products"] = keep
    raw = json.dumps(products, ensure_ascii=False, indent=2) + "\n"
    DemProductManifest.model_validate_json(raw)
    PRODUCTS.write_text(raw, encoding="utf-8")

    catalog = json.loads(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    sites = [s for s in catalog["sites"] if not str(s["id"]).startswith("pgda104_")]
    for _slug, (region, built, sha) in sorted(built_regions.items()):
        sites.append(catalog_entry(region, built, sha))
    catalog["sites"] = sites
    catalog["catalog_version"] = "e08b-2026-11-15-pgda104-regions"
    raw = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    Catalog.model_validate_json(raw)
    DEFAULT_CATALOG_PATH.write_text(raw, encoding="utf-8")
    print(f"index: {len(index_entries)} regions; catalog: {len(sites)} sites")


if __name__ == "__main__":
    main()
