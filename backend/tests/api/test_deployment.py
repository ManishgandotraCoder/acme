"""The Render blueprint (render.yaml) must stay wired to the app it deploys."""

from pathlib import Path

import pytest
import yaml

BLUEPRINT = Path(__file__).resolve().parents[3] / "render.yaml"


@pytest.fixture(scope="module")
def blueprint() -> dict:
    return yaml.safe_load(BLUEPRINT.read_text())


@pytest.fixture(scope="module")
def web(blueprint) -> dict:
    [service] = [s for s in blueprint["services"] if s["type"] == "web"]
    return service


def test_web_service_runs_the_production_docker_image(web):
    assert web["runtime"] == "docker"
    assert web["dockerfilePath"] == "./Dockerfile"


def test_health_check_points_at_a_live_endpoint(web, client):
    assert client.get(web["healthCheckPath"]).status_code == 200


def test_database_url_comes_from_the_declared_postgres_database(blueprint, web):
    env = {var["key"]: var for var in web["envVars"]}
    source = env["SALARY_DATABASE_URL"]["fromDatabase"]

    assert source["property"] == "connectionString"
    assert source["name"] in {db["name"] for db in blueprint["databases"]}
