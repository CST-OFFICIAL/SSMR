from datetime import datetime, timezone

from app.crop_rules import rank_crops
from app.schemas import SoilScan, SoilScanCreate


def sample_scan():
    payload = SoilScanCreate.model_validate({
        "source": "physical", "timestamp": datetime.now(timezone.utc).isoformat(),
        "soil_moisture": {"value": 40, "unit": "%", "status": "valid", "calibrated": True},
        "soil_temperature": {"value": 22, "unit": "°C", "status": "valid", "calibrated": True},
        "ph": {"value": 6.5, "unit": "pH", "status": "valid", "calibrated": True},
        "ec": {"value": 0.8, "unit": "mS/cm", "status": "valid", "calibrated": True},
    })
    return SoilScan(**payload.model_dump(), id="test", received_at=datetime.now(timezone.utc))


def test_crop_recommendations_disabled_without_cited_reference_rules(monkeypatch):
    monkeypatch.delenv("SSMR_CROP_RULES_PATH", raising=False)
    result = rank_crops(sample_scan(), region="test", season="test", water_availability="test")
    assert result["status"] == "unavailable_reference_data_required"
    assert result["items"] == []


def test_crop_ranking_requires_context_even_when_rules_exist(tmp_path):
    # Synthetic fixture tests the engine contract only; these values are not agricultural advice.
    rules = [{"crop": "Fixture Crop", "region": "Fixture Region", "season": "Fixture Season",
              "water_availability": "Fixture Water", "thresholds": {"ph": {"minimum": 5.0, "maximum": 8.0, "unit": "pH"}},
              "source_title": "Synthetic test fixture", "source_url": "https://example.org/test",
              "applicability_notes": "Synthetic fixture only; not a real crop recommendation."}]
    path = tmp_path / "rules.json"
    import json
    path.write_text(json.dumps(rules), encoding="utf-8")
    result = rank_crops(sample_scan(), region=None, season=None, water_availability=None, rules_path=str(path))
    assert result["status"] == "insufficient_context"
    assert result["items"] == []
