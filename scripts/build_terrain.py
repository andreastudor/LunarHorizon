"""Prepare separate calculation and visual products for the provisional PGDA 104 ROI."""

import json
import shutil
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from download_terrain import DEST, EXPECTED_SHA256, URL, sha256  # noqa: E402

from lunarhorizon.contracts.manifests import TerrainManifest  # noqa: E402

OUT = ROOT / "data/_cache/terrain/leibnitz_beta"
CITATION = "Bertone et al., Enhanced Topography Models, doi:10.3847/PSJ/ae5b70"


def main() -> None:
    if sha256(DEST) != EXPECTED_SHA256:
        raise ValueError("Sursa nu corespunde SHA-256 fixat")
    OUT.mkdir(parents=True, exist_ok=True)
    calc = OUT / "calculation.tif"
    shutil.copyfile(DEST, calc)
    lods = []
    with rasterio.open(calc) as ds:
        if ds.crs is None or ds.count != 1 or ds.width % 16 or ds.height % 16:
            raise ValueError("Raster incompatibil")
        source = ds.read(1, masked=True)
        invalid = np.ma.getmaskarray(source) | ~np.isfinite(source.data)
        # Every visual cell touched by an invalid source pixel stays invalid.
        for level, factor in enumerate((8, 16)):
            height, width = ds.height // factor, ds.width // factor
            valid = (~invalid).reshape(height, factor, width, factor).all(axis=(1, 3))
            safe = np.where(invalid, 0, source.data).astype(np.float64)
            avg = safe.reshape(height, factor, width, factor).mean(axis=(1, 3))
            visual = np.where(valid, avg, np.nan).astype("float32")
            name = f"visual_{factor}.tif"
            with rasterio.open(
                OUT / name,
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
                    "encoding": "GeoTIFF float32; NaN = NoData; blocuri complet valide",
                    "sha256": sha256(OUT / name),
                }
            )
        row = col = 1600
        x, y = ds.xy(row, col)
        lon, lat = transform(ds.crs, "+proj=longlat +R=1737400 +no_defs", [x], [y])
        if invalid[row, col]:
            raise ValueError("Pixelul reprezentativ este NoData")
        manifest = {
            "schema_version": "0.7.0",
            "terrain_id": "leibnitz_beta_provisional",
            "source": {
                "product_id": "pgda104_leibnitz_beta",
                "url": URL,
                "sha256": EXPECTED_SHA256,
                "citation": CITATION,
            },
            "frame_id": "MOON_ME_DE421",
            "crs": {"proj4": None, "wkt": ds.crs.to_wkt()},
            "reference_radius_m": 1737400.0,
            "vertical": {
                "units": "m",
                "reference": "Sferă 1737400 m (README produs)",
                "exaggeration_default_factor": 1,
            },
            "calc_resolution_m": float(ds.res[0]),
            "local_origin": {
                "latitude_deg": lat[0],
                "longitude_deg": lon[0],
                "elevation_m": float(source.data[row, col]),
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
                    "Model SfS; contribuția LROC neinspectată. "
                    "MOON_ME_DE421 este ipoteză neconfirmată."
                ),
            },
            "lods": lods,
        }
        # Densify projected edges before inverse projection; this is the raster extent,
        # not a claim of complete horizon coverage or a mask of valid pixels.
        b = ds.bounds
        xs: list[float] = []
        ys: list[float] = []
        corners = [
            (b.left, b.bottom),
            (b.right, b.bottom),
            (b.right, b.top),
            (b.left, b.top),
            (b.left, b.bottom),
        ]
        for start, end in pairwise(corners):
            for step in range(16):
                fraction = step / 16
                xs.append(start[0] + (end[0] - start[0]) * fraction)
                ys.append(start[1] + (end[1] - start[1]) * fraction)
        xs.append(xs[0])
        ys.append(ys[0])
        lons, lats = transform(ds.crs, "+proj=longlat +R=1737400 +no_defs", xs, ys)
        footprint = {
            "type": "Feature",
            "properties": {
                "meaning": "raster_extent_not_horizon_coverage",
                "frame_assumption": "MOON_ME_DE421 unconfirmed",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [list(map(list, zip(lons, lats, strict=True)))],
            },
        }
        (OUT / "raster_extent.geojson").write_text(
            json.dumps(footprint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    # Validate against both the Pydantic contract and its JSON representation.
    raw = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    TerrainManifest.model_validate_json(raw)
    (OUT / "terrain_manifest.json").write_text(raw, encoding="utf-8")
    print(f"Teren pregătit: {OUT}; calcul SHA-256 {sha256(calc)}")


if __name__ == "__main__":
    main()
