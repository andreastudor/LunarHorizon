"""E08b: terrain for several regions: selection, overlaps, edges, NoData, frames, status."""

import json
import shutil
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
from lunarhorizon.api.data import DataRegistry
from lunarhorizon.api.settings import DATA_DIR, Settings
from lunarhorizon.contracts.export import document_schema
from lunarhorizon.core.errors import ErrorCode
from lunarhorizon.core.projection import SouthPolarStereographic
from tests.support import SCHEMA_PATH, read_json

INDEX = read_json(DATA_DIR / "manifests" / "terrain_index.json")
ALL_BUILT = all(
    (DATA_DIR.parent / e["cache_dir"] / "calculation.tif").is_file() for e in INDEX["entries"]
)
real = pytest.mark.skipif(
    not ALL_BUILT, reason="PGDA 104 rasters missing; run acquire_pgda104.py and the build"
)
PROJECTION = SouthPolarStereographic()


def point(x_m: float, y_m: float) -> dict[str, float | str]:
    lat, lon = PROJECTION.inverse(x_m, y_m)
    return {"latitude_deg": lat, "longitude_deg": lon}


def problem(response: Any, status: int, code: ErrorCode) -> None:
    assert response.status_code == status, response.text
    assert response.json()["code"] == code.value


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


# --- real PGDA 104 products ---------------------------------------------------------------------


@real
def test_distinct_regions_select_their_own_product(client: TestClient) -> None:
    for entry in INDEX["entries"]:
        x_min, y_min, x_max, y_max = entry["bounds_m"]
        params = {**point((x_min + x_max) / 2, (y_min + y_max) / 2), "frame_id": "MOON_ME_DE421"}
        response = client.get("/api/terrain/manifest", params=params)
        assert response.status_code == 200, entry["terrain_id"]
        assert response.json()["terrain_id"] == entry["terrain_id"]


@real
def test_overlapping_rasters_use_the_deterministic_rule(client: TestClient) -> None:
    # Inside Leibnitz Beta [65-81 km x 110-126 km] and Nobile Rim 1 [74-94 km x 100-120 km]:
    # both samples valid, same resolution; edge distance 3 km vs 4 km -> Nobile Rim 1.
    params = {**point(78_000, 115_000), "frame_id": "MOON_ME_DE421"}
    chosen = {client.get("/api/terrain/manifest", params=params).json()["terrain_id"]}
    chosen |= {client.get("/api/terrain/manifest", params=params).json()["terrain_id"]}
    assert chosen == {"nobile_rim_1_provisional"}


@real
def test_point_on_a_raster_edge_keeps_the_product_but_has_no_height(client: TestClient) -> None:
    edge = point(65_001, 118_000)
    manifest = client.get("/api/terrain/manifest", params={**edge, "frame_id": "MOON_ME_DE421"})
    assert manifest.json()["terrain_id"] == "leibnitz_beta_provisional"
    sample = client.get(
        "/api/terrain/elevation", params={**edge, "terrain_id": "leibnitz_beta_provisional"}
    ).json()
    assert sample["elevation_m"] is None and sample["reason"] == "edge_or_nodata"


@real
def test_frames_are_not_mixed(client: TestClient) -> None:
    params = {**point(-38_000, 90_500), "frame_id": "MOON_ME_DE440_ME421"}  # inside Haworth
    problem(client.get("/api/terrain/manifest", params=params), 422, ErrorCode.UNSUPPORTED_FRAME)


@real
def test_points_without_a_downloaded_product(client: TestClient) -> None:
    # 88°S outside every PGDA 104 raster: PGDA 81 would cover it but was not acquired.
    far = point(*PROJECTION.forward(-88.0, 120.0))
    problem(
        client.get("/api/terrain/manifest", params={**far, "frame_id": "MOON_ME_DE421"}),
        503,
        ErrorCode.TERRAIN_DATA_MISSING,
    )
    # Chandrayaan-3 (69°S): south polar, no inventoried product → coverage unverified (404).
    problem(
        client.get("/api/terrain/manifest", params={"site_id": "chandrayaan3_vikram"}),
        404,
        ErrorCode.OUT_OF_DEM_COVERAGE,
    )


@real
def test_status_report_lists_products_and_sites(client: TestClient) -> None:
    report = client.get("/api/terrain/status").json()
    Draft202012Validator(document_schema(read_json(SCHEMA_PATH), "TerrainStatusReport")).validate(
        report
    )
    assert len(report["products"]) == 13
    assert {p["status"] for p in report["products"]} == {"available"}
    by_site = {s["site_id"]: s for s in report["sites"]}
    for entry in INDEX["entries"]:
        site = by_site[f"pgda104_{entry['slug']}_point"]
        assert site["status"] == "terrain_available"
        assert site["terrain_id"] == entry["terrain_id"]
    assert by_site["chandrayaan3_vikram"]["status"] == "coverage_unverified"
    assert by_site["chandrayaan3_planned_target"]["status"] == "coverage_unverified"
    assert by_site["apollo11_lm"]["status"] == "no_dem_coverage"


@real
def test_index_products_without_rasters_are_not_downloaded(tmp_path: Path) -> None:
    (tmp_path / "data" / "manifests").mkdir(parents=True)
    index = json.loads(json.dumps(INDEX))
    for entry in index["entries"]:
        name = entry["manifest"].replace("/", "_")
        shutil.copy(DATA_DIR.parent / entry["manifest"], tmp_path / name)
        entry["manifest"] = name
        entry["cache_dir"] = "absent"
    path = tmp_path / "data" / "manifests" / "terrain_index.json"
    path.write_text(json.dumps(index), encoding="utf-8")
    with TestClient(create_app(Settings(terrain_index_path=path))) as missing:
        report = missing.get("/api/terrain/status").json()
        assert {p["status"] for p in report["products"]} == {"not_downloaded"}
        params = {**point(78_000, 115_000), "frame_id": "MOON_ME_DE421"}
        problem(
            missing.get("/api/terrain/manifest", params=params),
            503,
            ErrorCode.TERRAIN_DATA_MISSING,
        )


# --- synthetic registry: NoData preference and frame filtering ----------------------------------


def synthetic_registry(tmp_path: Path) -> DataRegistry:
    """Three synthetic products overlapping around (65 050, 110 050) m."""
    root = tmp_path
    (root / "data" / "manifests").mkdir(parents=True)
    template = read_json(DATA_DIR / "manifests" / "leibnitz_terrain.json")
    entries = []
    specs = [
        ("a_synthetic", (65_000, 110_000), "MOON_ME_DE421", True),  # NoData everywhere
        ("b_synthetic", (65_010, 110_010), "MOON_ME_DE421", False),
        ("c_synthetic", (65_000, 110_000), "MOON_ME_DE440_ME421", False),
    ]
    for terrain_id, (x0, y0), frame, hole in specs:
        heights = np.full((20, 20), np.nan if hole else 100.0, dtype=np.float32)
        cache = root / "cache" / terrain_id
        cache.mkdir(parents=True)
        with rasterio.open(
            cache / "calculation.tif",
            "w",
            driver="GTiff",
            width=20,
            height=20,
            count=1,
            dtype="float32",
            crs=template["crs"]["wkt"],
            transform=from_origin(x0, y0 + 100, 5, 5),
            nodata=float("nan"),
        ) as ds:
            ds.write(heights, 1)
        manifest = dict(template)
        manifest["terrain_id"] = terrain_id
        manifest["frame_id"] = frame
        manifest["bounds"] = {
            "x_min_m": x0,
            "x_max_m": x0 + 100,
            "y_min_m": y0,
            "y_max_m": y0 + 100,
        }
        (root / f"{terrain_id}.json").write_text(json.dumps(manifest), encoding="utf-8")
        entries.append(
            {
                "terrain_id": terrain_id,
                "product_id": "synthetic",
                "region_name": terrain_id,
                "manifest": f"{terrain_id}.json",
                "cache_dir": f"cache/{terrain_id}",
                "bounds_m": [x0, y0, x0 + 100, y0 + 100],
                "calc_resolution_m": 5.0,
                "frame_id": frame,
            }
        )
    index = root / "data" / "manifests" / "terrain_index.json"
    index.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return DataRegistry(Settings(terrain_index_path=index))


def test_a_valid_sample_beats_a_nodata_product(tmp_path: Path) -> None:
    registry = synthetic_registry(tmp_path)
    lat, lon = PROJECTION.inverse(65_050, 110_050)
    selection = registry.select_terrain(lat, lon, "MOON_ME_DE421")
    # a_synthetic would win on terrain_id, but its sample is NoData.
    assert selection.status == "terrain_available"
    assert selection.entry is not None and selection.entry.manifest.terrain_id == "b_synthetic"


def test_frame_filters_the_candidates(tmp_path: Path) -> None:
    registry = synthetic_registry(tmp_path)
    lat, lon = PROJECTION.inverse(65_050, 110_050)
    other = registry.select_terrain(lat, lon, "MOON_ME_DE440_ME421")
    assert other.entry is not None and other.entry.manifest.terrain_id == "c_synthetic"
    # Only a_ (NoData, DE421) and c_ (DE440) cover this point: DE421 keeps a_, never c_.
    lat2, lon2 = PROJECTION.inverse(65_005, 110_005)
    only = registry.select_terrain(lat2, lon2, "MOON_ME_DE421")
    assert only.entry is not None and only.entry.manifest.terrain_id == "a_synthetic"


def test_a_point_outside_every_product(tmp_path: Path) -> None:
    registry = synthetic_registry(tmp_path)
    assert registry.select_terrain(0.67, 23.47, "MOON_ME_DE421").status == "no_dem_coverage"
    assert registry.select_terrain(-70.0, 30.0, "MOON_ME_DE421").status == "coverage_unverified"
