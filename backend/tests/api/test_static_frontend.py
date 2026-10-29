from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.api.conftest import StubLLM


def _client(tmp_path) -> TestClient:
    (tmp_path / "index.html").write_text("<html>spa</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    settings = Settings(database_url="sqlite://", static_dir=str(tmp_path))
    return TestClient(create_app(settings, llm=StubLLM()))


def test_serves_built_frontend_and_assets(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/").text == "<html>spa</html>"
        assert client.get("/assets/app.js").text == "console.log(1)"


def test_client_side_routes_fall_back_to_index(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/insights").text == "<html>spa</html>"


def test_unknown_api_paths_are_still_404(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/api/nope").status_code == 404
        assert client.get("/api/health").json() == {"status": "ok"}
