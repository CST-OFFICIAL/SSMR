from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .schemas import SoilScan

class Threshold(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum: float | None = None
    maximum: float | None = None
    unit: str = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def ordered_bounds(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("threshold minimum cannot exceed maximum")
        if self.minimum is None and self.maximum is None:
            raise ValueError("threshold must define a minimum or maximum")
        return self

class CropRule(BaseModel):
    """A threshold must be transcribed from a cited source applicable to its context."""
    model_config = ConfigDict(extra="forbid")
    crop: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=120)
    season: str = Field(min_length=1, max_length=80)
    water_availability: str = Field(min_length=1, max_length=80)
    thresholds: dict[str, Threshold] = Field(min_length=1)
    source_title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=8, max_length=1000)
    applicability_notes: str = Field(min_length=10, max_length=2000)

    @field_validator("source_url")
    @classmethod
    def require_web_reference(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) reference")
        return value

    @model_validator(mode="after")
    def supported_measurements_only(self):
        supported = {"soil_moisture", "soil_temperature", "ph", "ec"}
        unknown = set(self.thresholds) - supported
        if unknown:
            raise ValueError(f"unsupported measurement threshold(s): {sorted(unknown)}")
        return self


def load_rules(path: str | None = None) -> tuple[list[CropRule], list[str]]:
    """Load explicitly supplied rules. Missing/bad data disables recommendations."""
    configured = path or os.getenv("SSMR_CROP_RULES_PATH")
    if not configured:
        return [], ["No crop reference rules configured; recommendations are disabled."]
    file_path = Path(configured).expanduser()
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Rules file must contain a JSON array")
        rules = [CropRule.model_validate(item) for item in raw]
        return rules, []
    except (OSError, json.JSONDecodeError, ValueError, ValidationError) as exc:
        return [], [f"Crop reference rules could not be loaded: {type(exc).__name__}."]


def rank_crops(scan: SoilScan, *, region: str | None, season: str | None,
               water_availability: str | None, rules_path: str | None = None) -> dict[str, Any]:
    rules, warnings = load_rules(rules_path)
    if not rules:
        return {"status": "unavailable_reference_data_required", "items": [], "warnings": warnings}
    if not region or not season or not water_availability:
        return {"status": "insufficient_context", "items": [],
                "warnings": ["Region, growing season, and water availability are required for crop ranking."]}

    measurements = {
        "soil_moisture": scan.soil_moisture,
        "soil_temperature": scan.soil_temperature,
        "ph": scan.ph,
        "ec": scan.ec,
    }
    candidates: list[dict[str, Any]] = []
    for rule in rules:
        if rule.region.casefold() != region.casefold() or rule.season.casefold() != season.casefold():
            continue
        if rule.water_availability.casefold() != water_availability.casefold():
            continue
        reasons: list[str] = []
        eligible = True
        for name, threshold in rule.thresholds.items():
            measurement = measurements.get(name)
            if measurement is None or measurement.value is None or measurement.status.value != "valid":
                eligible = False
                reasons.append(f"Missing or invalid required measurement: {name}.")
                continue
            if measurement.calibrated is not True:
                eligible = False
                reasons.append(f"{name} is not confirmed calibrated.")
                continue
            if measurement.unit.casefold() != threshold.unit.casefold():
                eligible = False
                reasons.append(f"Unit mismatch for {name}: expected {threshold.unit}, received {measurement.unit}.")
                continue
            if threshold.minimum is not None and measurement.value < threshold.minimum:
                eligible = False
                reasons.append(f"{name} is below the cited rule's range.")
            if threshold.maximum is not None and measurement.value > threshold.maximum:
                eligible = False
                reasons.append(f"{name} is above the cited rule's range.")
        candidates.append({
            "crop": rule.crop,
            "eligible_under_supplied_rules": eligible,
            "status": "matches_supplied_thresholds" if eligible else "does_not_match_or_insufficient_data",
            "reasons": reasons,
            "reference": {"title": rule.source_title, "url": rule.source_url,
                          "applicability_notes": rule.applicability_notes,
                          "region": rule.region, "season": rule.season,
                          "water_availability": rule.water_availability},
            "ranking_note": "Rule match only; not a yield prediction or guarantee of agronomic suitability.",
        })
    if not candidates:
        return {"status": "no_applicable_rules", "items": [],
                "warnings": ["No cited rules match the supplied region, season, and water availability."]}
    candidates.sort(key=lambda item: (not item["eligible_under_supplied_rules"], item["crop"].casefold()))
    return {"status": "evaluated_with_cited_rules", "items": candidates, "warnings": warnings}
