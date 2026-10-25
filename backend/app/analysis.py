from __future__ import annotations

from typing import Any

from .schemas import AnalysisResult, MeasurementStatus, SoilScan
from .crop_rules import rank_crops


def analyze_scan(scan: SoilScan) -> AnalysisResult:
    """Report measurement quality and apply only explicitly configured, cited crop rules."""
    warnings = list(scan.warnings)
    findings: list[dict[str, Any]] = []
    measurements = {
        "soil_moisture": scan.soil_moisture,
        "soil_temperature": scan.soil_temperature,
        "ph": scan.ph,
        "ec": scan.ec,
    }
    usable = 0
    for name, measurement in measurements.items():
        measurement_status = measurement.status.value
        if measurement.value is None and measurement_status == MeasurementStatus.valid.value:
            measurement_status = MeasurementStatus.invalid.value
            warnings.append(f"{name}: marked valid but no numeric value was supplied")
        if measurement.value is not None and measurement.status != MeasurementStatus.valid:
            warnings.append(f"{name}: numeric value is present but status is {measurement.status.value}")
        if measurement.status == MeasurementStatus.valid and measurement.value is not None:
            usable += 1
        if measurement.calibrated is False:
            warnings.append(f"{name}: sensor is explicitly marked uncalibrated")
        findings.append({
            "measurement": name,
            "value": measurement.value,
            "unit": measurement.unit,
            "status": measurement_status,
            "calibrated": measurement.calibrated,
            "observed_at": measurement.observed_at.isoformat() if measurement.observed_at else None,
        })

    if scan.source.value == "simulated":
        warnings.append("This scan is simulated and must not be treated as a physical soil measurement.")
    if usable == 0:
        quality = "no_usable_measurements"
    elif usable < len(measurements):
        quality = "partial"
    elif any(m.calibrated is False for m in measurements.values()):
        quality = "uncalibrated"
    else:
        quality = "measurements_present_calibration_unverified"

    context = scan.agricultural_context
    crop_result = rank_crops(
        scan,
        region=context.region if context else None,
        season=context.season if context else None,
        water_availability=context.water_availability if context else None,
    )
    warnings.extend(crop_result["warnings"])
    return AnalysisResult(
        scan_id=scan.id,
        source=scan.source,
        data_quality=quality,
        measurement_findings=findings,
        warnings=list(dict.fromkeys(warnings)),
        crop_recommendations=crop_result["items"],
        crop_recommendations_status=crop_result["status"],
        explanation=(
            "This result reports measurement quality and applies only explicitly configured, cited crop rules. "
            "A rule match is not a yield prediction or guarantee of agronomic suitability. "
            "pH and electrical conductivity do not establish N-P-K nutrient levels."
        ),
    )
