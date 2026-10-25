from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import json
import os

from fastapi import FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import database
from .analysis import analyze_scan
from .schemas import AnalysisResult, SoilScan, SoilScanCreate
from .weather import get_weather

app = FastAPI(
    title="Smart Soil Monitoring Robot API",
    version="0.3.0",
    description="Laptop-first API for soil scans, scan history, and transparent measurement-quality analysis.",
)
# CORS origins are configurable; localhost defaults support laptop development.
_origins = [
    origin.strip()
    for origin in os.getenv(
        "SSMR_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ssmr-backend"}


@app.post("/api/v1/scans", response_model=SoilScan, status_code=status.HTTP_201_CREATED)
def create_scan(payload: SoilScanCreate) -> SoilScan:
    now = datetime.now(timezone.utc)
    scan = SoilScan(**payload.model_dump(), id=str(uuid4()), received_at=now)
    try:
        database.insert_scan(
            scan_id=scan.id,
            timestamp=scan.timestamp.isoformat(),
            received_at=scan.received_at.isoformat(),
            source=scan.source.value,
            payload=scan.model_dump(mode="json"),
        )
    except Exception as exc:
        # Keep implementation details out of API responses.
        raise HTTPException(status_code=500, detail="Could not persist scan") from exc
    return scan


@app.post("/api/v1/scans/batch", status_code=status.HTTP_201_CREATED)
def create_scans_batch(
    payloads: list[SoilScanCreate],
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=8, max_length=128),
) -> dict[str, object]:
    """Atomically ingest 1–50 buffered scans; optional key safely deduplicates retries."""
    if not 1 <= len(payloads) <= 50:
        raise HTTPException(status_code=422, detail="Batch must contain between 1 and 50 scans")

    received_at = datetime.now(timezone.utc)
    scans = [
        SoilScan(**payload.model_dump(), id=str(uuid4()), received_at=received_at)
        for payload in payloads
    ]
    records = [
        {
            "id": scan.id,
            "timestamp": scan.timestamp.isoformat(),
            "received_at": scan.received_at.isoformat(),
            "source": scan.source.value,
            "payload": scan.model_dump(mode="json"),
        }
        for scan in scans
    ]
    response_body = {
        "items": [scan.model_dump(mode="json") for scan in scans],
        "count": len(scans),
    }

    try:
        if idempotency_key:
            canonical_payload = json.dumps(
                [payload.model_dump(mode="json") for payload in payloads],
                sort_keys=True,
                separators=(",", ":"),
            )
            request_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
            replayed, stored_body = database.insert_scans_idempotent(
                records,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_body=response_body,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
            return stored_body

        database.insert_scans(records)
    except database.IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        # The transaction in the database layer rolls back the entire batch.
        raise HTTPException(status_code=500, detail="Could not persist scan batch") from exc

    response.headers["Idempotency-Replayed"] = "false"
    return response_body


@app.get("/api/v1/weather")
async def weather_for_location(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> dict[str, object]:
    """Fetch current conditions from Open-Meteo; unavailable data stays explicitly unavailable."""
    return await get_weather(latitude, longitude)


@app.get("/api/v1/scans")
def scan_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    scans, total = database.list_scans(limit=limit, offset=offset)
    return {"items": scans, "total": total, "limit": limit, "offset": offset}


@app.get("/api/v1/scans/{scan_id}", response_model=SoilScan)
def get_scan(scan_id: str) -> SoilScan:
    record = database.get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        return SoilScan.model_validate(record)
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Stored scan failed schema validation") from exc


@app.get("/api/v1/scans/{scan_id}/analysis", response_model=AnalysisResult)
def get_scan_analysis(scan_id: str) -> AnalysisResult:
    record = database.get_scan(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        scan = SoilScan.model_validate(record)
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Stored scan failed schema validation") from exc
    return analyze_scan(scan)
