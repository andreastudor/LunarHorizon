"""Automated validation of every terrain product in data/manifests/terrain_index.json.

For each built product: manifest valid for Pydantic and JSON Schema; cached manifest identical to
the versioned one; calculation raster identical to the pinned source (SHA-256); CRS, bounds and
pixel size equal to the manifest; each visual level with its SHA-256, geotransform, NoData mask
and block means recomputed from the calculation raster; the representative point equal to the
centre pixel
(height and latitude/longitude through the projection). Prints one line per product and fails on
the first inconsistency. Products not acquired are listed, not validated.

Usage: backend\\.venv\\Scripts\\python scripts\\verify_terrain_products.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from acquire_pgda104 import read_lock, sha256
from jsonschema import validate
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from lunarhorizon.contracts.manifests import TerrainManifest  # noqa: E402
from lunarhorizon.core.projection import SouthPolarStereographic  # noqa: E402

INDEX = ROOT / "data/manifests/terrain_index.json"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(entry: dict[str, object], schema: dict[str, object], pinned: dict[str, object]) -> str:
    terrain_id = str(entry["terrain_id"])
    raw = json.loads((ROOT / str(entry["manifest"])).read_text(encoding="utf-8"))
    manifest = TerrainManifest.model_validate(raw)
    validate(raw, {"$ref": "#/$defs/TerrainManifest", "$defs": schema["$defs"]})
    cache = ROOT / str(entry["cache_dir"])
    cached = json.loads((cache / "terrain_manifest.json").read_text(encoding="utf-8"))
    check(cached == raw, f"{terrain_id}: cached manifest differs from the versioned one")
    calc = cache / "calculation.tif"
    digest = sha256(calc)
    check(digest == pinned["sha256"], f"{terrain_id}: calculation raster differs from the source")
    check(manifest.source.sha256 == digest, f"{terrain_id}: manifest source SHA-256 differs")
    with rasterio.open(calc) as ds:
        b = manifest.bounds
        check(
            (ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
            == (b.x_min_m, b.y_min_m, b.x_max_m, b.y_max_m),
            f"{terrain_id}: bounds differ",
        )
        check(ds.res[0] == manifest.calc_resolution_m, f"{terrain_id}: resolution differs")
        check(ds.crs.to_wkt() == manifest.crs.wkt, f"{terrain_id}: CRS differs")
        data = ds.read(1, masked=True)
        invalid = np.ma.getmaskarray(data) | ~np.isfinite(data.data)
        check(
            abs(float(invalid.mean()) - (manifest.nodata.area_fraction or 0.0)) < 1e-12,
            f"{terrain_id}: NoData fraction differs",
        )
        for lod in manifest.lods:
            factor = round(lod.visual_resolution_m / ds.res[0])
            path = cache / lod.heights_path
            check(sha256(path) == lod.sha256, f"{terrain_id}: LOD {lod.level} SHA-256 differs")
            with rasterio.open(path) as visual:
                check(
                    visual.transform == ds.transform @ Affine.scale(factor),
                    f"{terrain_id}: LOD {lod.level} geotransform differs",
                )
                h, w = visual.height, visual.width
                check((w, h) == (lod.width_px, lod.height_px), f"{terrain_id}: LOD size differs")
                expected_valid = (~invalid).reshape(h, factor, w, factor).all(axis=(1, 3))
                safe = np.where(invalid, 0, data.data).astype(np.float64)
                means = safe.reshape(h, factor, w, factor).mean(axis=(1, 3))
                values = visual.read(1, masked=True)
                valid = ~np.ma.getmaskarray(values) & np.isfinite(values.data)
                check(np.array_equal(valid, expected_valid), f"{terrain_id}: LOD mask differs")
                check(
                    np.allclose(values.data[valid], means[valid], atol=0.001),
                    f"{terrain_id}: LOD means differ",
                )
        row, col = ds.height // 2, ds.width // 2
        origin = manifest.local_origin
        check(
            float(data.data[row, col]) == origin.elevation_m,
            f"{terrain_id}: representative height is not the centre pixel",
        )
        x, y = ds.xy(row, col)
        projection = SouthPolarStereographic(radius_m=manifest.reference_radius_m)
        px, py = projection.forward(origin.latitude_deg, origin.longitude_deg)
        check(abs(px - x) < 1e-3 and abs(py - y) < 1e-3, f"{terrain_id}: point not at centre")
    sizes = ", ".join(f"{lod.width_px}px@{lod.visual_resolution_m:g}m" for lod in manifest.lods)
    return f"{terrain_id}: OK ({ds.width}x{ds.height}@5m; LOD {sizes}; NoData {invalid.mean():.4%})"


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "data/schemas/lunarhorizon.schema.json").read_text("utf-8"))
    lock = read_lock()
    checked = 0
    for entry in index["entries"]:
        if not entry.get("manifest"):
            print(f"{entry['terrain_id']}: not acquired (listed, not validated)")
            continue
        print(verify(entry, schema, lock[str(entry["slug"])]))
        checked += 1
    print(f"{checked} products validated")


if __name__ == "__main__":
    main()
