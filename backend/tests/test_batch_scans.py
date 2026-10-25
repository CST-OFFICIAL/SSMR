from fastapi.testclient import TestClient

from app import database
from app.main import app


def _payload(timestamp):
    return {
        "source": "simulated",
        "timestamp": timestamp,
        "soil_moisture": {"value": 30, "unit": "%", "status": "valid", "calibrated": False},
    }


def test_batch_scan_ingestion_persists_all_items(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "batch.sqlite3"))
    database.init_db()
    client = TestClient(app)

    response = client.post("/api/v1/scans/batch", json=[
        _payload("2026-10-25T09:00:00Z"),
        _payload("2026-10-25T09:01:00Z"),
    ])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["count"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] != body["items"][1]["id"]
    history = client.get("/api/v1/scans")
    assert history.status_code == 200
    assert history.json()["total"] == 2


def test_batch_scan_rejects_empty_batch(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "empty-batch.sqlite3"))
    database.init_db()
    client = TestClient(app)

    response = client.post("/api/v1/scans/batch", json=[])
    assert response.status_code == 422
    assert client.get("/api/v1/scans").json()["total"] == 0


def test_batch_scan_validates_every_payload_before_writing(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "invalid-batch.sqlite3"))
    database.init_db()
    client = TestClient(app)

    response = client.post("/api/v1/scans/batch", json=[
        _payload("2026-10-25T09:00:00Z"),
        {"source": "physical", "timestamp": "not-a-timestamp"},
    ])
    assert response.status_code == 422
    assert client.get("/api/v1/scans").json()["total"] == 0


def test_batch_insert_rolls_back_every_item_on_database_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "atomic.sqlite3"))
    database.init_db()
    existing = {
        "id": "already-exists",
        "timestamp": "2026-10-25T09:00:00+00:00",
        "received_at": "2026-10-25T09:00:01+00:00",
        "source": "simulated",
        "payload": {"id": "already-exists"},
    }
    database.insert_scans([existing])

    new_record = {
        "id": "should-roll-back",
        "timestamp": "2026-10-25T09:02:00+00:00",
        "received_at": "2026-10-25T09:02:01+00:00",
        "source": "simulated",
        "payload": {"id": "should-roll-back"},
    }
    try:
        database.insert_scans([new_record, existing])
        assert False, "Expected duplicate primary key to fail"
    except Exception:
        pass

    assert database.get_scan("should-roll-back") is None
    assert database.get_scan("already-exists") is not None
