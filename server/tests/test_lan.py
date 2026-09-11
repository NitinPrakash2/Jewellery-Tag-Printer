"""Single-URL mode: the API server also serves the built client."""
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parent.parent.parent / "client" / "dist"


def test_serves_client_index(client):
    if not (DIST / "index.html").is_file():
        pytest.skip("client not built (run npm run build)")
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "root" in r.text


def test_api_still_wins_over_spa(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "db_ok" in r.json()


def test_unknown_path_falls_back_to_app(client):
    if not (DIST / "index.html").is_file():
        pytest.skip("client not built (run npm run build)")
    r = client.get("/some-page")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
