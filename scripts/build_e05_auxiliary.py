"""Prepare visual basemaps and report native-grid PGDA quality observations."""

import json
import shutil
import warnings

import numpy as np
import rasterio
from download_e05_auxiliary import IMAGE_SHA256, IMAGE_URL, QUALITY
from download_terrain import ROOT, sha256
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

OUT = ROOT / "data/_cache/e05_auxiliary"
IMAGE = ROOT / "data/_raw/basemaps/lroc_color_2k.jpg"
GEOGRAPHIC = "+proj=longlat +R=1737400 +no_defs"
POLAR = "+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m +no_defs"


def main() -> None:
    if sha256(IMAGE) != IMAGE_SHA256:
        raise ValueError("Textură diferită de suma fixată")
    OUT.mkdir(parents=True, exist_ok=True)
    texture = OUT / "globe.jpg"
    shutil.copyfile(IMAGE, texture)
    # The NASA JPEG is a texture without embedded CRS; its map transform is assigned below.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(IMAGE) as src:
            if src.count != 3 or (src.width, src.height) != (2048, 1024):
                raise ValueError("Dimensiune neașteptată a texturii NASA")
            rgb = src.read()
    global_path = OUT / "global_2d.tif"
    global_transform = from_bounds(-180, -90, 180, 90, 2048, 1024)
    with rasterio.open(
        global_path,
        "w",
        driver="GTiff",
        width=2048,
        height=1024,
        count=3,
        dtype="uint8",
        crs=GEOGRAPHIC,
        transform=global_transform,
        compress="deflate",
    ) as dst:
        dst.write(rgb)
    polar_path = OUT / "south_polar_2d.tif"
    polar_transform = from_bounds(-1000000, -1000000, 1000000, 1000000, 1024, 1024)
    projected = np.zeros((4, 1024, 1024), dtype="uint8")
    for i in range(3):
        reproject(
            rgb[i],
            projected[i],
            src_transform=global_transform,
            src_crs=GEOGRAPHIC,
            dst_transform=polar_transform,
            dst_crs=POLAR,
            resampling=Resampling.bilinear,
        )
    # A distinct alpha band, not black color, defines outside coverage.
    reproject(
        np.full((1024, 2048), 255, dtype="uint8"),
        projected[3],
        src_transform=global_transform,
        src_crs=GEOGRAPHIC,
        dst_transform=polar_transform,
        dst_crs=POLAR,
        resampling=Resampling.nearest,
    )
    with rasterio.open(
        polar_path,
        "w",
        driver="GTiff",
        width=1024,
        height=1024,
        count=4,
        dtype="uint8",
        crs=POLAR,
        transform=polar_transform,
        compress="deflate",
    ) as dst:
        dst.write(projected)
        dst.colorinterp = (
            rasterio.enums.ColorInterp.red,
            rasterio.enums.ColorInterp.green,
            rasterio.enums.ColorInterp.blue,
            rasterio.enums.ColorInterp.alpha,
        )
    quality = []
    x, y = 73002.5, 117997.5
    for name, digest in QUALITY.items():
        path = ROOT / "data/_raw/pgda104" / name
        if sha256(path) != digest:
            raise ValueError(f"Sumă incorectă: {name}")
        with rasterio.open(path) as ds:
            row, col = ds.index(x, y)
            pixel = ds.read(1, window=rasterio.windows.Window(col, row, 1, 1), masked=True)
            value = None if np.ma.getmaskarray(pixel)[0, 0] else float(pixel[0, 0])
            quality.append(
                {
                    "filename": name,
                    "sha256": digest,
                    "resolution_m": list(ds.res),
                    "bounds_m": list(ds.bounds),
                    "shape": [ds.height, ds.width],
                    "nodata": ds.nodata,
                    "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
                    "sample_xy_m": [x, y],
                    "sample_value": value,
                }
            )
    report = {
        "schema": "e05-auxiliary-v1",
        "source_url": IMAGE_URL,
        "source_sha256": IMAGE_SHA256,
        "credit": "NASA Scientific Visualization Studio",
        "usage": "NASA media guidelines; informational use, no endorsement",
        "image_limit": (
            "Aesthetic product; polar gaps use lower-resolution LOLA albedo; not scientific data"
        ),
        "source_map_center_longitude_deg": 0,
        "files": [
            {"name": p.name, "sha256": sha256(p), "size_bytes": p.stat().st_size}
            for p in (texture, global_path, polar_path)
        ],
        "quality_frame_assumption": "MOON_ME_DE421 unconfirmed",
        "quality_files": quality,
        "quality_note": (
            "NAC image counts and solar bins are not LOLA shot counts; "
            "GLDSIGM definition unconfirmed."
        ),
        "quality_indicators": {
            "nac_image_count": {
                "file": "A310_GLDMASK_005.tif",
                "native_resolution_m": 15.0,
                "status": "shown_separately_no_thresholds",
            },
            "solar_azimuth_categories": {
                "file": "A310_GLDSBCT_005.tif",
                "native_resolution_m": 15.0,
                "status": "shown_separately_no_thresholds",
            },
            "gldsigm": {
                "file": "A310_GLDSIGM_005.tif",
                "native_resolution_m": 5.0,
                "status": "uninterpreted_excluded_from_validated_quality_indicators",
                "note": (
                    "Archive README names GLDISGM; the ZIP contains GLDSIGM; the PGDA 104 page, "
                    "the Zenodo record page and the regions README do not define it."
                ),
            },
        },
        "resolution_source": ("read from each GeoTIFF transform; not inferred from the '005' name"),
        "checksum_kinds": {
            "zip_member_crc": "verified by zipfile when each member is read",
            "local_sha256": "computed by this project after first acquisition and pinned",
            "provider_published_md5": (
                "published for whole archives only; whole-archive MD5 not verified"
            ),
        },
        "product_decisions": {
            "scope": "product approvals for implementation; not GEO/ASTRO scientific validation",
            "D-05_D-06_D-10": (
                "sphere 1737400 m and CRS read from raster; "
                "MOON_ME_DE421 stays a hypothesis; no frame conversion"
            ),
            "D-07": (
                "PGDA 104 and Leibnitz Beta Plateau representative point for the first "
                "provisional demonstration; not a landing site, not a validated two-site selection"
            ),
            "D-11": (
                "NASA SVS backgrounds provisional for display; credit and resolution limits above"
            ),
            "D-19": (
                "NAC counts and solar-azimuth categories shown separately; "
                "no invented thresholds; not LOLA measurement counts"
            ),
        },
    }
    (OUT / "auxiliary_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Produse auxiliare: {OUT}")


if __name__ == "__main__":
    main()
