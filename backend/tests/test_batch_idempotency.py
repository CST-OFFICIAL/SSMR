from fastapi.testclient import TestClient

from app import database
from app.main import app


def _payload(timestamp, moisture=30):
    return {
        "source": "simulated",
        "timestamp": timestamp,
        "soil_moisture": {"value": moisture, "unit": "%", "status": "valid", "calibrated": False},
    }


def test_batch_retry_with_same_key_returns_original_scans(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "idempotent.sqlite3"))
    database.init_db()
    client = TestClient(app)
    payload = [_payload("2026-10-25T09:00:00Z"), _payload("2026-10-25T09:01:00Z")]
    headers = {"Idempotency-Key": "robot-01-batch-0001"}

    first = client.post("/api/v1/scans/batch", json=payload, headers=headers)
    retry = client.post("/api/v1/scans/batch", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert retry.status_code == 201, retry.text
    assert [item["id"] for item in retry.json()["items"]] == [item["id"] for item in first.json()["items"]]
    assert first.headers["idempotency-replayed"] == "false"
    assert retry.headers["idempotency-replayed"] == "true"
    assert client.get("/api/v1/scans").json()["total"] == 2


def test_reusing_idempotency_key_with_different_payload_returns_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "idempotency-conflict.sqlite3"))
    database.init_db()
    client = TestClient(app)
    headers = {"Idempotency-Key": "robot-01-batch-0002"}

    first = client.post("/api/v1/scans/batch", json=[_payload("2026-10-25T09:00:00Z")], headers=headers)
    conflict = client.post(
        "/api/v1/scans/batch",
        json=[_payload("2026-10-25T09:00:00Z", moisture=42)],
        headers=headers,
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert client.get("/api/v1/scans").json()["total"] == 1


def test_idempotency_key_must_be_at_least_eight_characters(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "idempotency-header.sqlite3"))
    database.init_db()
    client = TestClient(app)

    response = client.post(
        "/api/v1/scans/batch",
        json=[_payload("2026-10-25T09:00:00Z")],
        headers={"Idempotency-Key": "short"},
    )
    assert response.status_code == 422
    assert client.get("/api/v1/scans").json()["total"] == 0
