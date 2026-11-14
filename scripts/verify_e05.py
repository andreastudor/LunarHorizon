"""Verify generated E05 products, manifests and visual downsampling."""

import json
import sys

import numpy as np
import rasterio
from download_e05_auxiliary import IMAGE_SHA256, QUALITY
from download_terrain import DEST, EXPECTED_SHA256, ROOT, sha256
from jsonschema import validate
from rasterio.transform import Affine

sys.path.insert(0, str(ROOT / "backend"))
from lunarhorizon.contracts.manifests import DemProductManifest, TerrainManifest
from lunarhorizon.terrain.sampling import sample_bilinear


def main() -> None:
    terrain = ROOT / "data/_cache/terrain/leibnitz_beta"
    aux = ROOT / "data/_cache/e05_auxiliary"
    manifest_path = ROOT / "data/manifests/leibnitz_terrain.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    product_path = ROOT / "data/manifests/terrain_products.json"
    product = json.loads(product_path.read_text(encoding="utf-8"))
    TerrainManifest.model_validate_json(json.dumps(manifest))
    DemProductManifest.model_validate_json(json.dumps(product))
    schema = json.loads(
        (ROOT / "data/schemas/lunarhorizon.schema.json").read_text(encoding="utf-8")
    )
    for name, doc in (("TerrainManifest", manifest), ("DemProductManifest", product)):
        validate(doc, {"$ref": f"#/$defs/{name}", "$defs": schema["$defs"]})
    if manifest != json.loads((terrain / "terrain_manifest.json").read_text(encoding="utf-8")):
        raise ValueError("Manifestul generat nu corespunde celui versionat")
    if sha256(DEST) != EXPECTED_SHA256 or sha256(terrain / "calculation.tif") != EXPECTED_SHA256:
        raise ValueError("Rasterul de calcul diferă de sursă")
    with rasterio.open(DEST) as ds:
        source = ds.read(1, masked=True)
        invalid = np.ma.getmaskarray(source) | ~np.isfinite(source.data)
        x, y = ds.xy(1600, 1600)
        if sample_bilinear(DEST, x, y) != float(source.data[1600, 1600]):
            raise ValueError("Eșantionul nu corespunde pixelului original")
        for lod, factor in zip(manifest["lods"], (8, 16), strict=True):
            path = terrain / lod["heights_path"]
            if sha256(path) != lod["sha256"]:
                raise ValueError("SHA-256 vizual incorect")
            with rasterio.open(path) as visual:
                if visual.transform != ds.transform @ Affine.scale(factor):
                    raise ValueError("Transformarea vizuală este incorectă")
                h, w = visual.height, visual.width
                expected_valid = (~invalid).reshape(h, factor, w, factor).all(axis=(1, 3))
                safe = np.where(invalid, 0, source.data).astype(np.float64)
                means = safe.reshape(h, factor, w, factor).mean(axis=(1, 3))
                values = visual.read(1, masked=True)
                actual_valid = ~np.ma.getmaskarray(values) & np.isfinite(values.data)
                if not np.array_equal(actual_valid, expected_valid):
                    raise ValueError("Mască vizuală incorectă")
                if not np.allclose(values.data[actual_valid], means[actual_valid], atol=0.001):
                    raise ValueError("Medii vizuale incorecte")
    auxiliary = json.loads((aux / "auxiliary_manifest.json").read_text(encoding="utf-8"))
    archived_aux = json.loads(
        (ROOT / "data/manifests/e05_auxiliary.json").read_text(encoding="utf-8")
    )
    if auxiliary != archived_aux:
        raise ValueError("Manifestul auxiliar generat diferă de cel versionat")
    if auxiliary["source_sha256"] != IMAGE_SHA256:
        raise ValueError("Sursă hartă necunoscută")
    for entry in auxiliary["files"]:
        if sha256(aux / entry["name"]) != entry["sha256"]:
            raise ValueError("SHA-256 fundal incorect")
    for entry in auxiliary["quality_files"]:
        path = ROOT / "data/_raw/pgda104" / entry["filename"]
        if sha256(path) != QUALITY[entry["filename"]]:
            raise ValueError("SHA-256 calitate incorect")
        with rasterio.open(path) as ds:
            row, col = ds.index(*entry["sample_xy_m"])
            sample = ds.read(1, window=rasterio.windows.Window(col, row, 1, 1), masked=True)
            if np.ma.getmaskarray(sample)[0, 0] or float(sample[0, 0]) != entry["sample_value"]:
                raise ValueError("Eșantion calitate incorect")
            if list(ds.res) != entry["resolution_m"]:
                raise ValueError("Rezoluție calitate incorectă")
    with rasterio.open(aux / "global_2d.tif") as ds:
        if ds.width != 2048 or ds.height != 1024 or ds.count != 3:
            raise ValueError("Fundal global incompatibil")
    with rasterio.open(aux / "south_polar_2d.tif") as ds:
        if ds.width != 1024 or ds.height != 1024 or ds.count != 4:
            raise ValueError("Fundal polar incompatibil")
    print("Manifestele, rasterele, nivelurile vizuale, fundalurile și calitatea sunt verificate.")


if __name__ == "__main__":
    main()
