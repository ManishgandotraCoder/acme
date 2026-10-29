import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def spa_client(make_client, tmp_path) -> TestClient:
    (tmp_path / "index.html").write_text("<html>spa</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    with make_client(static_dir=str(tmp_path)) as client:
        yield client


def test_serves_built_frontend_and_assets(spa_client):
    assert spa_client.get("/").text == "<html>spa</html>"
    assert spa_client.get("/assets/app.js").text == "console.log(1)"


def test_client_side_routes_fall_back_to_index(spa_client):
    assert spa_client.get("/insights").text == "<html>spa</html>"


def test_unknown_api_paths_are_still_404(spa_client):
    assert spa_client.get("/api/nope").status_code == 404
    assert spa_client.get("/api/health").json() == {"status": "ok"}
