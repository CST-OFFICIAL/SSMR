from datetime import datetime, timezone

from app.analysis import analyze_scan
from app.schemas import SoilScan, SoilScanCreate


def make_scan(*, source="physical", moisture=None, temperature=None, ph=None, ec=None):
    payload = {
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "soil_moisture": moisture or {"value": None, "unit": "%", "status": "unavailable"},
        "soil_temperature": temperature or {"value": None, "unit": "°C", "status": "unavailable"},
        "ph": ph or {"value": None, "unit": "pH", "status": "unavailable"},
        "ec": ec or {"value": None, "unit": "mS/cm", "status": "unavailable"},
    }
    created = SoilScanCreate.model_validate(payload)
    return SoilScan(**created.model_dump(), id="analysis-fixture", received_at=datetime.now(timezone.utc))


def test_analysis_marks_all_unavailable_measurements_as_no_usable_measurements():
    result = analyze_scan(make_scan())
    assert result.data_quality == "no_usable_measurements"
    assert result.crop_recommendations == []
    assert result.crop_recommendations_status == "unavailable_reference_data_required"


def test_analysis_flags_valid_status_without_numeric_value():
    result = analyze_scan(make_scan(
        moisture={"value": None, "unit": "%", "status": "valid"}
    ))
    assert result.data_quality == "no_usable_measurements"
    assert any("marked valid but no numeric value" in warning for warning in result.warnings)
    moisture = next(item for item in result.measurement_findings if item["measurement"] == "soil_moisture")
    assert moisture["status"] == "invalid"


def test_analysis_warns_when_value_is_present_but_status_is_invalid():
    result = analyze_scan(make_scan(
        ph={"value": 6.2, "unit": "pH", "status": "invalid"}
    ))
    assert any("numeric value is present but status is invalid" in warning for warning in result.warnings)
    ph = next(item for item in result.measurement_findings if item["measurement"] == "ph")
    assert ph["status"] == "invalid"


def test_analysis_warns_for_simulated_source():
    result = analyze_scan(make_scan(source="simulated"))
    assert any("simulated" in warning.lower() for warning in result.warnings)


def test_analysis_labels_all_readings_uncalibrated_when_flagged():
    valid = {"value": 1, "unit": "%", "status": "valid", "calibrated": False}
    result = analyze_scan(make_scan(
        moisture=valid,
        temperature={"value": 20, "unit": "°C", "status": "valid", "calibrated": False},
        ph={"value": 6, "unit": "pH", "status": "valid", "calibrated": False},
        ec={"value": 0.5, "unit": "mS/cm", "status": "valid", "calibrated": False},
    ))
    assert result.data_quality == "uncalibrated"
    assert sum("explicitly marked uncalibrated" in warning for warning in result.warnings) == 4
