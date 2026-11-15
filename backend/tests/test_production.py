"""Production UI/API routing and the cross-origin headers needed by Pages."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lunarhorizon.api.production import create_production_app, production_origins


def test_public_ui_api_and_cors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "index.html").write_text("<title>synthetic_frontend</title>", encoding="utf-8")
    monkeypatch.setenv("LUNAR_ALLOWED_ORIGINS", "https://andreastudor.github.io")
    with TestClient(create_production_app(tmp_path)) as client:
        assert "synthetic_frontend" in client.get("/").text
        assert "sites" in client.get("/api/sites").json()
        response = client.get("/api/sites", headers={"Origin": "https://andreastudor.github.io"})
        assert response.headers["access-control-allow-origin"] == "https://andreastudor.github.io"
        assert "X-Width" in response.headers["access-control-expose-headers"]
        denied = client.get("/api/sites", headers={"Origin": "https://unlisted.example"})
        assert "access-control-allow-origin" not in denied.headers
        assert client.get("/api/does-not-exist").status_code == 404
        assert client.get("/data/manifests/kernels.json").status_code == 404


def test_production_requires_built_ui(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Frontend build missing"):
        create_production_app(tmp_path)


@pytest.mark.parametrize(
    "value", ["*", "https://example.com/path", "https://user:pass@example.com"]
)
def test_cors_rejects_invalid_origin(value: str) -> None:
    with pytest.raises(ValueError):
        production_origins(value)
