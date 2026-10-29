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


@pytest.fixture(scope="module")
def env(web) -> dict:
    return {var["key"]: var for var in web["envVars"]}


@pytest.mark.parametrize("secret", ["SALARY_DATABASE_URL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"])
def test_secrets_are_entered_in_the_dashboard_never_committed(env, secret):
    assert env[secret]["sync"] is False
    assert "value" not in env[secret]


def test_settings_that_are_not_secret_are_committed_with_the_blueprint(env):
    assert env["SALARY_LLM_PROVIDER"]["value"] == "anthropic"
