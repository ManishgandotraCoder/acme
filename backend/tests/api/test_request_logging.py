import logging


def test_every_response_carries_a_request_id(client):
    response = client.get("/api/health")
    assert len(response.headers["X-Request-ID"]) == 32


def test_incoming_request_id_is_propagated(client):
    response = client.get("/api/health", headers={"X-Request-ID": "trace-abc-123"})
    assert response.headers["X-Request-ID"] == "trace-abc-123"


def test_each_request_is_logged_with_status_and_duration(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/employees/999", headers={"X-Request-ID": "req-1"})

    [record] = [r for r in caplog.records if r.name == "app.request"]
    assert record.request_id == "req-1"
    assert (record.method, record.path, record.status) == ("GET", "/api/employees/999", 404)
    assert record.duration_ms >= 0


def test_readiness_checks_the_database(client):
    assert client.get("/api/ready").json() == {"status": "ready", "database": "ok"}
