# SSMR cross-agent integration contract (v0.1)

This document is the hand-off contract between the Raspberry Pi/robot agent, backend agent, and frontend agent. It describes the backend branch as currently implemented; it does not claim physical sensors have been integrated or calibrated.

## Ownership boundaries

- Robot agent: physical sensor drivers, calibration routines, robot/motor control, and emitting a scan payload.
- Backend agent: this API, persistence, data-quality analysis, weather lookup, and reviewed/cited crop rules.
- Frontend agent: dashboard, scan/history views, and user interactions.
- Shared contract changes should be discussed before changing field names or units. Avoid editing another agent's owned directory.

## Backend URL and health

- Local API: `http://127.0.0.1:8000`
- Health check: `GET /health`
- Interactive API docs: `GET /docs`
- Browser origins for local Vite are allowed by default. Set `SSMR_CORS_ORIGINS` to a comma-separated allowlist for another frontend origin.

## Create a scan

Send `POST /api/v1/scans` with JSON. The `source` field is required; use `physical` only for actual device measurements and `simulated` for mock/demo data.

```json
{
  "source": "simulated",
  "timestamp": "2026-10-25T09:00:00Z",
  "location": {
    "latitude": 26.75,
    "longitude": 94.63
  },
  "agricultural_context": {
    "region": "Assam",
    "season": "kharif",
    "water_availability": "rainfed"
  },
  "soil_moisture": {
    "value": 32.5,
    "unit": "%",
    "status": "valid",
    "calibrated": false,
    "observed_at": "2026-10-25T08:59:58Z"
  },
  "soil_temperature": {
    "value": 24.0,
    "unit": "°C",
    "status": "valid",
    "calibrated": false
  },
  "ph": {
    "value": 6.4,
    "unit": "pH",
    "status": "valid",
    "calibrated": false
  },
  "ec": {
    "value": null,
    "unit": "mS/cm",
    "status": "unavailable",
    "calibrated": null
  },
  "robot_status": {
    "device_id": "prototype-01"
  },
  "warnings": []
}
```

A successful create returns HTTP `201` and includes a generated `id` and `received_at`. Timestamps must include a timezone (prefer ISO 8601 UTC with `Z`). Unknown fields are rejected.

### Measurement rules

Each measurement uses:
- `value`: finite number or `null`; never substitute zero for a missing sensor reading.
- `unit`: explicit string. Current expected units are `%`, `°C`, `pH`, and `mS/cm`, but the API does not convert units.
- `status`: `valid`, `invalid`, or `unavailable`.
- `calibrated`: `true`, `false`, or `null`; do not mark true unless the sensor calibration process has actually been completed.
- `observed_at`: optional timezone-aware timestamp.

The robot agent must document the exact sensor model, raw output, conversion, units, and calibration method before real readings are marked calibrated. The backend does not currently infer NPK or diagnose fertility from pH/moisture/temperature/EC.

## Read data

- `GET /api/v1/scans?limit=50&offset=0` — newest-first history; response keys: `items`, `total`, `limit`, `offset`.
- `GET /api/v1/scans/{id}` — stored scan.
- `GET /api/v1/scans/{id}/analysis` — measurement findings, warnings, quality status, and crop recommendation status.
- `GET /api/v1/weather?latitude={lat}&longitude={lon}` — current weather; check the returned availability/staleness fields before displaying it.

Use `id` as the stable scan identifier. Handle HTTP `404` for missing scans, HTTP `422` for invalid payloads, and weather responses that explicitly report unavailable data. Do not present simulated readings as physical measurements.

## Crop recommendation safety

Crop recommendations remain unavailable unless the backend is configured with reviewed, applicable, cited crop rules and the relevant measurements/context are sufficient. Do not hardcode crop names or thresholds in the frontend. Display the backend's recommendation status and warnings rather than inventing a recommendation when the list is empty.

## Run locally

From the repository root:

```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

A GitHub Actions workflow runs the backend tests on relevant pushes and pull requests once this workflow is present on the branch.
