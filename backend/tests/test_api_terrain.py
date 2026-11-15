"""E08: altitudinea observatorului din rasterul de calcul și nivelurile vizuale ale terenului."""

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from rasterio.transform import from_origin

from lunarhorizon.api.app import create_app
from lunarhorizon.api.settings import DATA_DIR, Settings
from lunarhorizon.contracts.export import document_schema
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.core.errors import ErrorCode
from lunarhorizon.core.projection import SouthPolarStereographic
from tests.support import SCHEMA_PATH, read_json

TERRAIN_DIR = DATA_DIR / "_cache" / "terrain" / "leibnitz_beta"
MANIFEST_PATH = DATA_DIR / "manifests" / "leibnitz_terrain.json"
MANIFEST = TerrainManifest.model_validate_json(MANIFEST_PATH.read_text(encoding="utf-8"))
real_terrain = pytest.mark.skipif(
    not (TERRAIN_DIR / "calculation.tif").is_file(),
    reason="produsele E05 lipsesc; rulați scripts/download_terrain.py și build_terrain.py",
)
SCHEMA = read_json(SCHEMA_PATH)


def problem(response: Any, status: int, code: ErrorCode) -> None:
    assert response.status_code == status, response.text
    assert response.json()["code"] == code.value


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def origin_params() -> dict[str, float | str]:
    return {
        "terrain_id": MANIFEST.terrain_id,
        "latitude_deg": MANIFEST.local_origin.latitude_deg,
        "longitude_deg": MANIFEST.local_origin.longitude_deg,
    }


# --- altitudinea observatorului ------------------------------------------------------------------


@real_terrain
def test_elevation_at_the_local_origin_equals_the_manifest_value(client: TestClient) -> None:
    response = client.get("/api/terrain/elevation", params=origin_params())
    assert response.status_code == 200
    document = response.json()
    Draft202012Validator(document_schema(SCHEMA, "TerrainSample")).validate(document)
    # Originea este centrul unui pixel al rasterului de calcul: bilinear = valoarea pixelului.
    assert document["elevation_m"] == pytest.approx(MANIFEST.local_origin.elevation_m, abs=1e-3)
    assert document["reason"] is None
    assert document["frame_id"] == MANIFEST.frame_id == "MOON_ME_DE421"
    assert document["calc_resolution_m"] == 5.0


@real_terrain
def test_elevation_is_null_with_reason_at_the_raster_edge(client: TestClient) -> None:
    bounds = MANIFEST.bounds
    projection = SouthPolarStereographic(radius_m=MANIFEST.reference_radius_m)
    lat, lon = projection.inverse(bounds.x_min_m + 1.0, bounds.y_max_m - 1.0)
    params: dict[str, str | float] = {
        "terrain_id": MANIFEST.terrain_id,
        "latitude_deg": lat,
        "longitude_deg": lon,
    }
    response = client.get("/api/terrain/elevation", params=params)
    assert response.status_code == 200
    assert response.json()["elevation_m"] is None
    assert response.json()["reason"] == "edge_or_nodata"


def test_elevation_outside_the_raster_is_404(client: TestClient) -> None:
    params: dict[str, str | float] = {
        "terrain_id": MANIFEST.terrain_id,
        "latitude_deg": 0.674,
        "longitude_deg": 23.47,
    }
    problem(client.get("/api/terrain/elevation", params=params), 404, ErrorCode.OUT_OF_DEM_COVERAGE)


def test_elevation_validates_its_parameters(client: TestClient) -> None:
    for params in (
        {**origin_params(), "terrain_id": "unknown_terrain"},
        {**origin_params(), "terrain_id": "../etc"},
        {**origin_params(), "latitude_deg": 95},
        {"terrain_id": MANIFEST.terrain_id},
    ):
        problem(
            client.get("/api/terrain/elevation", params=params), 422, ErrorCode.VALIDATION_ERROR
        )


# --- nivelurile vizuale -------------------------------------------------------------------------


@real_terrain
@pytest.mark.parametrize("level", [lod.level for lod in MANIFEST.lods])
def test_lod_bytes_equal_the_visual_geotiff(client: TestClient, level: int) -> None:
    lod = next(item for item in MANIFEST.lods if item.level == level)
    response = client.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/{level}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["x-width"] == str(lod.width_px)
    assert response.headers["x-height"] == str(lod.height_px)
    values = np.frombuffer(response.content, dtype="<f4").reshape(lod.height_px, lod.width_px)
    with rasterio.open(TERRAIN_DIR / lod.heights_path) as ds:
        expected = ds.read(1)
    assert np.array_equal(np.isnan(values), np.isnan(expected))
    assert np.array_equal(values[~np.isnan(values)], expected[~np.isnan(expected)])


def test_lod_rejects_unknown_identifiers_and_levels(client: TestClient) -> None:
    problem(
        client.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/7"), 422, ErrorCode.VALIDATION_ERROR
    )
    problem(client.get("/api/terrain/unknown/lods/0"), 422, ErrorCode.VALIDATION_ERROR)
    problem(client.get("/api/terrain/BAD$ID/lods/0"), 422, ErrorCode.VALIDATION_ERROR)
    problem(
        client.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/x"), 422, ErrorCode.VALIDATION_ERROR
    )


def synthetic_terrain(tmp_path: Path, heights: np.ndarray, sha: str | None = None) -> Settings:
    """Manifest și raster vizual sintetice, cu georeferențierea manifestului real."""
    rows, cols = heights.shape
    resolution = (MANIFEST.bounds.x_max_m - MANIFEST.bounds.x_min_m) / cols
    raster = tmp_path / "synthetic_visual.tif"
    transform = from_origin(
        MANIFEST.bounds.x_min_m, MANIFEST.bounds.y_max_m, resolution, resolution
    )
    with rasterio.open(
        raster,
        "w",
        driver="GTiff",
        width=cols,
        height=rows,
        count=1,
        dtype="float32",
        crs=MANIFEST.crs.wkt,
        transform=transform,
        nodata=float("nan"),
    ) as ds:
        ds.write(heights.astype(np.float32), 1)
    digest = sha or hashlib.sha256(raster.read_bytes()).hexdigest()
    document = json.loads(MANIFEST.model_dump_json())
    document["lods"] = [
        {
            "level": 0,
            "visual_resolution_m": resolution,
            "width_px": cols,
            "height_px": rows,
            "heights_path": raster.name,
            "encoding": "GeoTIFF float32; NaN = NoData (synthetic)",
            "sha256": digest,
        }
    ]
    manifest = tmp_path / "synthetic_manifest.json"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    (tmp_path / "calculation.tif").write_bytes(b"synthetic_placeholder")
    return Settings(
        terrain_manifest_path=manifest, terrain_calculation_raster=tmp_path / "calculation.tif"
    )


def test_lod_keeps_nodata_as_nan_never_zero(tmp_path: Path) -> None:
    # Rânduri: nord → sud (rasterul vizual are originea în colțul de nord-vest, rezoluție pozitivă).
    heights = np.array([[1.0, np.nan, 0.0, 4.0], [5.0, 6.0, np.nan, 8.0]], dtype=np.float32)
    with TestClient(create_app(synthetic_terrain(tmp_path, heights))) as synthetic:
        response = synthetic.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/0")
    assert response.status_code == 200
    values = np.frombuffer(response.content, dtype="<f4").reshape(2, 4)
    assert np.isnan(values[0, 1]) and np.isnan(values[1, 2])
    assert values[0, 2] == 0.0  # zero real rămâne zero
    assert values[0, 0] == 1.0 and values[1, 3] == 8.0


def test_lod_with_altered_checksum_is_refused(tmp_path: Path) -> None:
    heights = np.ones((2, 2), dtype=np.float32)
    with TestClient(create_app(synthetic_terrain(tmp_path, heights, sha="0" * 64))) as altered:
        problem(
            altered.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/0"),
            503,
            ErrorCode.TERRAIN_DATA_MISSING,
        )


def test_lod_with_missing_file_is_refused(tmp_path: Path) -> None:
    settings = synthetic_terrain(tmp_path, np.ones((2, 2), dtype=np.float32))
    (tmp_path / "synthetic_visual.tif").unlink()
    with TestClient(create_app(settings)) as missing:
        problem(
            missing.get(f"/api/terrain/{MANIFEST.terrain_id}/lods/0"),
            503,
            ErrorCode.TERRAIN_DATA_MISSING,
        )
