from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

class DataSource(str, Enum):
    simulated = "simulated"
    physical = "physical"

class MeasurementStatus(str, Enum):
    valid = "valid"
    invalid = "invalid"
    unavailable = "unavailable"

class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float | None = None
    unit: str = Field(min_length=1, max_length=24)
    status: MeasurementStatus = MeasurementStatus.unavailable
    calibrated: bool | None = None
    observed_at: datetime | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float | None) -> float | None:
        if value is not None and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("measurement value must be finite")
        return value

class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class SoilScanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: DataSource
    location: Location | None = None
    soil_moisture: Measurement = Field(default_factory=lambda: Measurement(unit="%"))
    soil_temperature: Measurement = Field(default_factory=lambda: Measurement(unit="°C"))
    ph: Measurement = Field(default_factory=lambda: Measurement(unit="pH"))
    ec: Measurement = Field(default_factory=lambda: Measurement(unit="mS/cm"))
    robot_status: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value

class SoilScan(SoilScanCreate):
    id: str
    received_at: datetime

class AnalysisResult(BaseModel):
    scan_id: str
    source: DataSource
    data_quality: str
    measurement_findings: list[dict[str, Any]]
    warnings: list[str]
    crop_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    crop_recommendations_status: str = "unavailable_reference_data_required"
    explanation: str
