from datetime import datetime, timezone
import json

from app.crop_rules import rank_crops
from app.schemas import SoilScan, SoilScanCreate


def _scan(*, ph_calibrated=True, ph_unit="pH"):
    created = SoilScanCreate.model_validate({
        "source": "physical",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agricultural_context": {
            "region": "Fixture Region",
            "season": "Fixture Season",
            "water_availability": "Fixture Water",
        },
        "soil_moisture": {"value": 40, "unit": "%", "status": "valid", "calibrated": True},
        "soil_temperature": {"value": 22, "unit": "°C", "status": "valid", "calibrated": True},
        "ph": {"value": 6.5, "unit": ph_unit, "status": "valid", "calibrated": ph_calibrated},
        "ec": {"value": 0.8, "unit": "mS/cm", "status": "valid", "calibrated": True},
    })
    return SoilScan(**created.model_dump(), id="fixture-scan", received_at=datetime.now(timezone.utc))


def _rules_file(tmp_path):
    path = tmp_path / "fixture-rules.json"
    path.write_text(json.dumps([{
        "crop": "Fixture Crop",
        "region": "Fixture Region",
        "season": "Fixture Season",
        "water_availability": "Fixture Water",
        "thresholds": {"ph": {"minimum": 5.5, "maximum": 7.0, "unit": "pH"}},
        "source_title": "Synthetic test fixture",
        "source_url": "https://example.org/synthetic-fixture",
        "applicability_notes": "Synthetic fixture for automated tests only; not agricultural advice.",
    }]), encoding="utf-8")
    return str(path)


def test_rule_match_requires_valid_calibrated_measurement(tmp_path):
    result = rank_crops(
        _scan(), region="Fixture Region", season="Fixture Season",
        water_availability="Fixture Water", rules_path=_rules_file(tmp_path),
    )
    assert result["status"] == "evaluated_with_cited_rules"
    assert result["items"][0]["eligible_under_supplied_rules"] is True


def test_rule_match_rejects_uncalibrated_measurement(tmp_path):
    result = rank_crops(
        _scan(ph_calibrated=False), region="Fixture Region", season="Fixture Season",
        water_availability="Fixture Water", rules_path=_rules_file(tmp_path),
    )
    assert result["items"][0]["eligible_under_supplied_rules"] is False
    assert any("not confirmed calibrated" in reason for reason in result["items"][0]["reasons"])


def test_rule_match_rejects_unit_mismatch(tmp_path):
    result = rank_crops(
        _scan(ph_unit="unknown-unit"), region="Fixture Region", season="Fixture Season",
        water_availability="Fixture Water", rules_path=_rules_file(tmp_path),
    )
    assert result["items"][0]["eligible_under_supplied_rules"] is False
    assert any("Unit mismatch" in reason for reason in result["items"][0]["reasons"])


def test_malformed_rules_disable_recommendations(tmp_path):
    path = tmp_path / "broken-rules.json"
    path.write_text("{not-json", encoding="utf-8")
    result = rank_crops(
        _scan(), region="Fixture Region", season="Fixture Season",
        water_availability="Fixture Water", rules_path=str(path),
    )
    assert result["status"] == "unavailable_reference_data_required"
    assert result["items"] == []
    assert result["warnings"]
