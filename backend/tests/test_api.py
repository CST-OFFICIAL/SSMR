from fastapi.testclient import TestClient

from app.main import app
from app import database


def test_scan_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    database.init_db()
    client = TestClient(app)

    response = client.post("/api/v1/scans", json={
        "source": "simulated",
        "timestamp": "2026-10-25T09:00:00Z",
        "soil_moisture": {"value": 32.5, "unit": "%", "status": "valid", "calibrated": False},
        "soil_temperature": {"value": 24, "unit": "°C", "status": "valid", "calibrated": False},
        "ph": {"value": 6.4, "unit": "pH", "status": "valid", "calibrated": False},
        "ec": {"value": None, "unit": "mS/cm", "status": "unavailable"}
    })
    assert response.status_code == 201, response.text
    scan = response.json()
    assert scan["source"] == "simulated"
    assert scan["id"]
    assert __import__("datetime").datetime.fromisoformat(scan["received_at"].replace("Z", "+00:00")).tzinfo is not None

    history = client.get("/api/v1/scans")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["id"] == scan["id"]

    detail = client.get(f"/api/v1/scans/{scan['id']}")
    assert detail.status_code == 200
    assert detail.json()["ph"]["value"] == 6.4

    analysis = client.get(f"/api/v1/scans/{scan['id']}/analysis")
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["data_quality"] == "partial"
    assert result["crop_recommendations"] == []
    assert result["crop_recommendations_status"] == "unavailable_reference_data_required"
    assert any("simulated" in warning.lower() for warning in result["warnings"])


def test_missing_scan_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "empty.sqlite3"))
    database.init_db()
    client = TestClient(app)
    assert client.get("/api/v1/scans/not-a-real-id").status_code == 404


def test_rejects_timezone_naive_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("SSMR_DATABASE_PATH", str(tmp_path / "validation.sqlite3"))
    database.init_db()
    client = TestClient(app)
    response = client.post("/api/v1/scans", json={"source": "physical", "timestamp": "2026-10-25T09:00:00"})
    assert response.status_code == 422
