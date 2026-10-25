from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import SoilScanCreate


def test_scan_rejects_unknown_top_level_fields():
    with pytest.raises(ValidationError):
        SoilScanCreate.model_validate({"source": "simulated", "unexpected": "value"})


def test_scan_rejects_timezone_naive_timestamp():
    with pytest.raises(ValidationError):
        SoilScanCreate.model_validate({
            "source": "physical",
            "timestamp": "2026-10-25T09:00:00",
        })


def test_measurement_rejects_non_finite_values():
    with pytest.raises(ValidationError):
        SoilScanCreate.model_validate({
            "source": "physical",
            "soil_moisture": {
                "value": float("inf"),
                "unit": "%",
                "status": "valid",
            },
        })


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 0), (-91, 0), (0, 181), (0, -181)],
)
def test_location_rejects_out_of_range_coordinates(latitude, longitude):
    with pytest.raises(ValidationError):
        SoilScanCreate.model_validate({
            "source": "physical",
            "location": {"latitude": latitude, "longitude": longitude},
        })


def test_timestamp_default_is_timezone_aware():
    scan = SoilScanCreate.model_validate({"source": "simulated"})
    assert scan.timestamp.tzinfo is not None
    assert scan.timestamp.utcoffset() is not None
