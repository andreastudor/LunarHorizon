"""E06: endpointurile HTTP, validarea cererilor, erorile și consistența cu motorul astronomic."""

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from lunarhorizon.api import jobs
from lunarhorizon.api.app import create_app
from lunarhorizon.api.settings import Settings
from lunarhorizon.astro.bodies import ObserverSite, body_direction
from lunarhorizon.astro.kernels import DEFAULT_KERNEL_DIR, load_profile
from lunarhorizon.catalog import load_catalog
from lunarhorizon.contracts.export import document_schema
from lunarhorizon.contracts.manifests import TerrainManifest
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from tests.support import REPO_ROOT, SCHEMA_PATH, read_json

KERNELS_PRESENT = (DEFAULT_KERNEL_DIR / "de440s.bsp").is_file()
SCHEMA = read_json(SCHEMA_PATH)
LEIBNITZ_POINT = {"latitude_deg": -85.4266039743, "longitude_deg": 31.7441821732}


def valid_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "sites": [
            {"custom": {"label": "synthetic_pol", "latitude_deg": -89.5, "longitude_deg": 10}}
        ],
        "frame_id": "MOON_ME_DE440_ME421",
        "start_utc": "2026-11-15T00:00:00Z",
        "end_utc": "2026-11-16T00:00:00Z",
        "observer_height_m": 2,
        "solar_criterion": "disc_center",
        "earth_criterion": {"kind": "center_above_horizon", "min_elevation_deg": 0},
        "terrain_mode": "idealized_local_plane",
        "series_step_s": 3600,
    }
    body.update(changes)
    return body


def check_schema(document: Any, name: str) -> None:
    Draft202012Validator(document_schema(SCHEMA, name)).validate(document)


def assert_problem(response: Any, status: int, code: ErrorCode) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["code"] == code.value and problem["status"] == status
    check_schema(problem, "Problem")
    return problem  # type: ignore[no-any-return]


def wait_done(client: TestClient, simulation_id: str, timeout_s: float = 120.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = client.get(f"/api/simulations/{simulation_id}").json()
        if body["status"] in ("done", "failed"):
            return body  # type: ignore[no-any-return]
        time.sleep(0.05)
    raise AssertionError("simularea nu s-a terminat")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def no_kernels(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(kernel_dir=tmp_path))) as test_client:
        yield test_client


@pytest.fixture
def with_dem(tmp_path: Path) -> Iterator[TestClient]:
    raster = tmp_path / "synthetic_calculation.tif"
    raster.write_bytes(b"synthetic")
    settings = Settings(terrain_calculation_raster=raster)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


# --- sites, health, OpenAPI --------------------------------------------------------------------


def test_sites_returns_the_catalog_document(client: TestClient) -> None:
    response = client.get("/api/sites")
    assert response.status_code == 200
    document = response.json()
    check_schema(document, "Catalog")
    expected = load_catalog()
    assert document["catalog_version"] == expected.catalog_version
    assert [s["id"] for s in document["sites"]] == [s.id for s in expected.sites]
    # E08b: Leibnitz Beta is exposed as a DEM-region representative point, not as a landing site.
    leibnitz = next(s for s in document["sites"] if "leibnitz" in s["id"])
    assert leibnitz["status"] == "dem_region"
    assert leibnitz["position_kind"] == "representative_point"


def test_openapi_lists_all_endpoints(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    assert set(paths) == {
        "/api/health",
        "/api/sites",
        "/api/coverage",
        "/api/terrain/manifest",
        "/api/simulations",
        "/api/simulations/{simulation_id}",
        "/api/assets/{name}",
        "/api/terrain/elevation",
        "/api/terrain/status",
        "/api/terrain/{terrain_id}/lods/{level}",
    }


@pytest.mark.skipif(not KERNELS_PRESENT, reason="kernelurile lipsesc")
@pytest.mark.kernels
def test_health_ok_and_coverage(client: TestClient) -> None:
    health = client.get("/api/health").json()
    check_schema(health, "Health")
    assert health["status"] == "ok" and health["kernels_loaded"] is True
    coverage = client.get("/api/coverage").json()
    check_schema(coverage, "Coverage")
    assert coverage["temporal"]["kernel_profile"] == "de440_me421"
    assert coverage["temporal"]["start_utc"].startswith("1849-12-25")
    de421 = client.get("/api/coverage", params={"frame_id": "MOON_ME_DE421"}).json()
    assert de421["temporal"]["kernel_profile"] == "de421"


def test_missing_kernels_degrade_health_and_fail_with_503(no_kernels: TestClient) -> None:
    health = no_kernels.get("/api/health").json()
    check_schema(health, "Health")
    assert health["status"] == "degraded" and health["kernels_loaded"] is False
    assert health["issues"]
    assert_problem(no_kernels.get("/api/coverage"), 503, ErrorCode.KERNEL_MISSING)
    response = no_kernels.post("/api/simulations", json=valid_body())
    assert_problem(response, 503, ErrorCode.KERNEL_MISSING)


# --- validarea cererii ------------------------------------------------------------------------


def test_invalid_requests_are_rejected_before_kernels_are_needed(no_kernels: TestClient) -> None:
    site = valid_body()["sites"][0]
    cases: list[tuple[dict[str, Any], ErrorCode]] = [
        (valid_body(sites=[site] * 5), ErrorCode.TOO_MANY_SITES),
        (valid_body(sites=[]), ErrorCode.VALIDATION_ERROR),
        (valid_body(frame_id="MOON_ME"), ErrorCode.UNSUPPORTED_FRAME),
        (valid_body(frame_id="IAU_MOON"), ErrorCode.UNSUPPORTED_FRAME),
        (valid_body(end_utc="2026-11-14T00:00:00Z"), ErrorCode.VALIDATION_ERROR),
        (valid_body(start_utc="2026-11-15T00:00:00"), ErrorCode.VALIDATION_ERROR),
        (valid_body(start_utc="2026-11-15T23:59:60Z"), ErrorCode.VALIDATION_ERROR),
        (valid_body(observer_height_m=-1), ErrorCode.VALIDATION_ERROR),
        (valid_body(terrain_mode="auto"), ErrorCode.VALIDATION_ERROR),
        (valid_body(unknown_field=1), ErrorCode.VALIDATION_ERROR),
        (valid_body(series_step_s=0), ErrorCode.VALIDATION_ERROR),
        (
            valid_body(sites=[{"custom": {**site["custom"], "latitude_deg": 91}}]),
            ErrorCode.VALIDATION_ERROR,
        ),
        (valid_body(sites=[{"site_id": "nu_exista"}]), ErrorCode.VALIDATION_ERROR),
        (valid_body(sites=[{"site_id": "apollo11_lm"}] * 2), ErrorCode.VALIDATION_ERROR),
        (
            valid_body(start_utc="2020-01-01T00:00:00Z", end_utc="2022-01-01T00:00:00Z"),
            ErrorCode.INTERVAL_TOO_LONG,
        ),
        (valid_body(end_utc="2026-12-15T00:00:00Z", series_step_s=1), ErrorCode.VALIDATION_ERROR),
    ]
    missing_frame = valid_body()
    del missing_frame["frame_id"]
    cases.append((missing_frame, ErrorCode.VALIDATION_ERROR))
    for body, code in cases:
        problem = assert_problem(no_kernels.post("/api/simulations", json=body), 422, code)
        assert problem["detail"]


def test_malformed_json_and_wrong_types_are_validation_errors(client: TestClient) -> None:
    response = client.post(
        "/api/simulations", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert_problem(response, 422, ErrorCode.VALIDATION_ERROR)
    response = client.post("/api/simulations", json=valid_body(observer_height_m="2"))
    problem = assert_problem(response, 422, ErrorCode.VALIDATION_ERROR)
    assert any(error["loc"][-1] == "observer_height_m" for error in problem["field_errors"])


def test_catalog_site_in_another_frame_is_refused_without_conversion(
    no_kernels: TestClient,
) -> None:
    body = valid_body(sites=[{"site_id": "apollo11_lm"}], frame_id="MOON_ME_DE421")
    problem = assert_problem(
        no_kernels.post("/api/simulations", json=body), 422, ErrorCode.UNSUPPORTED_FRAME
    )
    assert "nicio transformare" in problem["detail"]


def test_dem_mode_is_refused_not_replaced_by_idealized(no_kernels: TestClient) -> None:
    body = valid_body(terrain_mode="dem")
    problem = assert_problem(
        no_kernels.post("/api/simulations", json=body), 422, ErrorCode.OUT_OF_DEM_COVERAGE
    )
    assert "idealized_local_plane" in problem["detail"]


def test_unknown_simulation_id_is_404(client: TestClient) -> None:
    assert_problem(
        client.get("/api/simulations/sim-necunoscut"), 404, ErrorCode.SIMULATION_NOT_FOUND
    )


# --- terenul ----------------------------------------------------------------------------------


def test_health_lists_dem_only_when_the_raster_exists(with_dem: TestClient, tmp_path: Path) -> None:
    with TestClient(
        create_app(Settings(terrain_calculation_raster=tmp_path / "absent.tif"))
    ) as bare:
        assert bare.get("/api/health").json()["dem_products"] == []
    assert with_dem.get("/api/health").json()["dem_products"] == ["pgda104_leibnitz_beta"]


@pytest.mark.skipif(not KERNELS_PRESENT, reason="kernelurile lipsesc")
@pytest.mark.kernels
def test_coverage_terrain_footprint_comes_from_the_raster_extent(with_dem: TestClient) -> None:
    coverage = with_dem.get("/api/coverage").json()
    check_schema(coverage, "Coverage")
    (product,) = coverage["terrain"]
    assert product["product_id"] == "pgda104_leibnitz_beta" and product["role"] == "near"
    assert -86.0 < product["min_latitude_deg"] < product["max_latitude_deg"] < -85.0
    ring = product["footprint"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert all(0.0 < lon < 60.0 for lon, _ in ring)


def test_terrain_manifest_for_a_point_inside_the_raster(with_dem: TestClient) -> None:
    response = with_dem.get("/api/terrain/manifest", params=LEIBNITZ_POINT)
    assert response.status_code == 200
    check_schema(response.json(), "TerrainManifest")
    expected = TerrainManifest.model_validate_json(
        (REPO_ROOT / "data/manifests/leibnitz_terrain.json").read_text(encoding="utf-8")
    )
    assert response.json() == json.loads(expected.model_dump_json())
    assert response.json()["terrain_id"].endswith("provisional")


def test_terrain_manifest_outside_the_raster_is_404(with_dem: TestClient) -> None:
    for params in (
        {"latitude_deg": 0.67416, "longitude_deg": 23.47314},
        {"latitude_deg": -85.4266039743, "longitude_deg": -148.0},
        {"latitude_deg": 90.0, "longitude_deg": 0.0},
    ):
        assert_problem(
            with_dem.get("/api/terrain/manifest", params=params), 404, ErrorCode.OUT_OF_DEM_COVERAGE
        )
    assert_problem(
        with_dem.get("/api/terrain/manifest", params={"site_id": "apollo11_lm"}),
        404,
        ErrorCode.OUT_OF_DEM_COVERAGE,
    )


def test_terrain_manifest_requires_the_raster_on_disk(client: TestClient, tmp_path: Path) -> None:
    settings = Settings(terrain_calculation_raster=tmp_path / "absent.tif")
    with TestClient(create_app(settings)) as missing:
        response = missing.get("/api/terrain/manifest", params=LEIBNITZ_POINT)
    assert_problem(response, 503, ErrorCode.TERRAIN_DATA_MISSING)


def test_terrain_manifest_validates_parameters(with_dem: TestClient) -> None:
    cases: tuple[dict[str, str | float], ...] = (
        {},
        {"site_id": "apollo11_lm", **LEIBNITZ_POINT},
        {"latitude_deg": -85.0},
        {"latitude_deg": 95.0, "longitude_deg": 0.0},
        {"site_id": "nu_exista"},
    )
    for params in cases:
        assert_problem(
            with_dem.get("/api/terrain/manifest", params=params), 422, ErrorCode.VALIDATION_ERROR
        )


# --- fluxul complet cu kerneluri ------------------------------------------------------------


@pytest.mark.kernels
@pytest.mark.skipif(not KERNELS_PRESENT, reason="kernelurile lipsesc")
class TestSimulationFlow:
    def test_request_result_flow_matches_the_engine(self, client: TestClient) -> None:
        body = valid_body(
            sites=[
                {"site_id": "apollo11_lm"},
                {"custom": {"label": "synthetic_pol", "latitude_deg": -89.5, "longitude_deg": 10}},
            ]
        )
        accepted = client.post("/api/simulations", json=body)
        assert accepted.status_code == 202
        check_schema(accepted.json(), "SimulationAccepted")
        assert accepted.json()["cache_hit"] is False
        status = wait_done(client, accepted.json()["id"])
        assert status["status"] == "done" and status["error"] is None
        check_schema(status, "SimulationStatus")
        result = status["result"]
        assert result["request"]["series_step_s"] == 3600
        assert [s["site_ref"] for s in result["sites"]] == ["apollo11_lm", "custom-2"]
        profile = load_profile("de440_me421")
        site = next(s for s in load_catalog().sites if s.id == "apollo11_lm")
        observer = ObserverSite(site.latitude_deg, site.longitude_deg, 0.0, 2.0)
        series = result["series"][0]
        for index in (0, 5, len(series["time_utc"]) - 1):
            direct = body_direction(profile, observer, "sun", series["time_utc"][index], "LT+S")
            assert series["sun"]["elevation_deg"][index] == direct.elevation_deg
            assert series["sun"]["azimuth_deg"][index] == direct.azimuth_deg
        assert result["horizon"][0]["mode"] == "idealized_local_plane"
        assert result["terrain"][0]["available"] is False
        assert result["provenance"]["source_mode"] == "live"

    def test_same_request_returns_the_same_simulation(self, client: TestClient) -> None:
        first = client.post("/api/simulations", json=valid_body())
        done = wait_done(client, first.json()["id"])
        second = client.post("/api/simulations", json=valid_body())
        assert second.status_code == 200
        assert second.json() == {"id": first.json()["id"], "status": "done", "cache_hit": True}
        again = client.get(f"/api/simulations/{first.json()['id']}").json()
        assert again == done

    def test_explicit_and_default_step_resolve_to_the_same_simulation(
        self, client: TestClient
    ) -> None:
        implicit = valid_body()
        implicit.pop("series_step_s")
        resolved = client.post("/api/simulations", json=implicit).json()["id"]
        explicit = client.post("/api/simulations", json=valid_body(series_step_s=60)).json()["id"]
        assert resolved == explicit  # 1 zi → pasul implicit este 60 s (≤ 1500 de puncte)

    def test_different_requests_get_different_ids(self, client: TestClient) -> None:
        a = client.post("/api/simulations", json=valid_body()).json()["id"]
        b = client.post("/api/simulations", json=valid_body(observer_height_m=3)).json()["id"]
        assert a != b

    def test_outside_ephemeris_coverage_is_422_with_real_limits(self, client: TestClient) -> None:
        body = valid_body(start_utc="1800-01-01T00:00:00Z", end_utc="1800-01-02T00:00:00Z")
        problem = assert_problem(
            client.post("/api/simulations", json=body), 422, ErrorCode.OUT_OF_EPHEMERIS_COVERAGE
        )
        assert problem["coverage_start_utc"].startswith("1849-12-25")
        assert problem["coverage_end_utc"].startswith("2150-01-21")

    def test_de421_profile_has_its_own_narrower_coverage(self, client: TestClient) -> None:
        body = valid_body(
            frame_id="MOON_ME_DE421",
            start_utc="2060-01-01T00:00:00Z",
            end_utc="2060-01-02T00:00:00Z",
        )
        problem = assert_problem(
            client.post("/api/simulations", json=body), 422, ErrorCode.OUT_OF_EPHEMERIS_COVERAGE
        )
        assert problem["coverage_end_utc"].startswith("2050-12-31")

    def test_concurrent_requests_all_complete_and_match(self, client: TestClient) -> None:
        bodies = [valid_body(observer_height_m=2 + index) for index in range(4)]
        ids: list[str] = []
        lock = threading.Lock()

        def post(body: dict[str, Any]) -> None:
            response = client.post("/api/simulations", json=body)
            with lock:
                ids.append(response.json()["id"])

        threads = [threading.Thread(target=post, args=(body,)) for body in bodies]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert len(set(ids)) == 4
        for simulation_id in ids:
            assert wait_done(client, simulation_id)["status"] == "done"

    def test_failed_simulation_reports_a_problem_without_internal_details(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*_: Any, **__: Any) -> Any:
            raise RuntimeError("detaliu intern secret")

        monkeypatch.setattr(jobs, "simulate_idealized", boom)
        accepted = client.post("/api/simulations", json=valid_body()).json()
        status = wait_done(client, accepted["id"])
        assert status["status"] == "failed" and status["result"] is None
        check_schema(status, "SimulationStatus")
        assert status["error"]["code"] == "INTERNAL_ERROR"
        assert "secret" not in json.dumps(status)

    def test_failed_simulation_with_domain_error_keeps_its_code(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*_: Any, **__: Any) -> Any:
            raise LunarHorizonError(ErrorCode.TERRAIN_DATA_MISSING, "lipsește rasterul")

        monkeypatch.setattr(jobs, "simulate_idealized", refuse)
        status = wait_done(client, client.post("/api/simulations", json=valid_body()).json()["id"])
        assert status["status"] == "failed"
        assert status["error"]["code"] == "TERRAIN_DATA_MISSING"
        assert status["error"]["status"] == 503

    def test_cache_keeps_a_bounded_number_of_finished_simulations(self) -> None:
        with TestClient(create_app(Settings(cache_size=1))) as small:
            ids = []
            for height in (2, 3, 4):
                accepted = small.post("/api/simulations", json=valid_body(observer_height_m=height))
                ids.append(accepted.json()["id"])
                wait_done(small, accepted.json()["id"])
            assert small.get(f"/api/simulations/{ids[0]}").status_code == 404
            assert small.get(f"/api/simulations/{ids[2]}").status_code == 200


# --- resurse statice E05 --------------------------------------------------------------------


def asset_client(tmp_path: Path, content: bytes, listed_sha: str) -> TestClient:
    (tmp_path / "globe.jpg").write_bytes(content)
    manifest = tmp_path / "aux.json"
    manifest.write_text(
        json.dumps({"files": [{"name": "globe.jpg", "sha256": listed_sha}]}), encoding="utf-8"
    )
    return TestClient(
        create_app(Settings(auxiliary_dir=tmp_path, auxiliary_manifest_path=manifest))
    )


def test_asset_is_served_only_when_listed_and_checksum_matches(tmp_path: Path) -> None:
    import hashlib

    content = b"synthetic_jpeg"
    good = hashlib.sha256(content).hexdigest()
    with asset_client(tmp_path, content, good) as served:
        response = served.get("/api/assets/globe.jpg")
        assert response.status_code == 200 and response.content == content
        assert response.headers["content-type"] == "image/jpeg"
        assert_problem(served.get("/api/assets/other.jpg"), 422, ErrorCode.VALIDATION_ERROR)
    with asset_client(tmp_path, content, "0" * 64) as altered:
        assert_problem(altered.get("/api/assets/globe.jpg"), 503, ErrorCode.TERRAIN_DATA_MISSING)


def test_missing_asset_is_reported_not_replaced(tmp_path: Path) -> None:
    manifest = tmp_path / "aux.json"
    manifest.write_text(json.dumps({"files": [{"name": "globe.jpg", "sha256": "0" * 64}]}))
    settings = Settings(auxiliary_dir=tmp_path / "absent", auxiliary_manifest_path=manifest)
    with TestClient(create_app(settings)) as missing:
        assert_problem(missing.get("/api/assets/globe.jpg"), 503, ErrorCode.TERRAIN_DATA_MISSING)
