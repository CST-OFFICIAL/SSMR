from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import database
from .analysis import analyze_scan
from .schemas import AnalysisResult, SoilScan, SoilScanCreate

app = FastAPI(
    title="Smart Soil Monitoring Robot API",
    version="0.1.0",
    description="Laptop-first API for soil scans, scan history, and transparent measurement-quality analysis.",
)
# CORS origins are configurable; localhost defaults support laptop development.
import os
_origins = [origin.strip() for origin in os.getenv("SSMR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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
