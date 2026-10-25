# SSMR cross-agent integration contract (v0.3)

This document is the hand-off contract between the Raspberry Pi/robot agent, backend agent, and frontend agent. It describes the backend API on the current development branch; it does not claim physical sensors have been integrated or calibrated.

## Ownership boundaries

- Robot agent: physical sensor drivers, calibration routines, robot/motor control, and emitting scan payloads.
- Backend agent: API, persistence, data-quality analysis, weather lookup, and reviewed/cited crop rules.
- Frontend agent: dashboard, scan/history views, and user interactions.
- Shared contract changes should be discussed before changing field names or units. Avoid editing another agent's owned directory.

## Backend URL and health

- Local API: `http://127.0.0.1:8000`
- Health check: `GET /health`
- Interactive API docs: `GET /docs`
- Browser origins for local Vite are allowed by default. Set `SSMR_CORS_ORIGINS` to a comma-separated allowlist for another frontend origin.

## Create one scan

Send `POST /api/v1/scans` with a JSON object. The `source` field is required; use `physical` only for actual device measurements and `simulated` for mock/demo data.

```json
{
  "source": "simulated",
  "timestamp": "2026-10-25T09:00:00Z",
  "location": {"latitude": 26.75, "longitude": 94.63},
  "agricultural_context": {
    "region": "Assam",
    "season": "kharif",
    "water_availability": "rainfed"
  },
  "soil_moisture": {
    "value": 32.5, "unit": "%", "status": "valid",
    "calibrated": false, "observed_at": "2026-10-25T08:59:58Z"
  },
  "soil_temperature": {
    "value": 24.0, "unit": "°C", "status": "valid", "calibrated": false
  },
  "ph": {
    "value": 6.4, "unit": "pH", "status": "valid", "calibrated": false
  },
  "ec": {
    "value": null, "unit": "mS/cm", "status": "unavailable", "calibrated": null
  },
  "robot_status": {"device_id": "prototype-01"},
  "warnings": []
}
```

A successful create returns HTTP `201` and includes a generated `id` and `received_at`. Timestamps must include a timezone (prefer ISO 8601 UTC with `Z`). Unknown fields are rejected.

## Batch upload for buffered scans

When the robot has cached scans while disconnected, send a JSON array of 1–50 scan payloads to `POST /api/v1/scans/batch`. Every item uses the same schema as a single scan.

Example:

```json
[
  {"source": "simulated", "timestamp": "2026-10-25T09:00:00Z"},
  {"source": "simulated", "timestamp": "2026-10-25T09:01:00Z"}
]
```

For safe retries, include a unique `Idempotency-Key` header (8–128 characters), for example:

```http
Idempotency-Key: robot-01-batch-0001
```

- First accepted request returns `201` and `Idempotency-Replayed: false`.
- Repeating the same key with the same payload returns the original scan IDs and response without duplicate database rows; header is `Idempotency-Replayed: true`.
- Reusing a key with a different payload returns HTTP `409 Conflict`.
- Without the header, retries can create duplicate scans.
- A batch must contain 1–50 items. Invalid payloads return `422`; database errors roll back the whole batch.

The idempotency key and original response are stored in the same SQLite transaction as the scans, so retry protection survives API process restarts while that database is retained.

## Measurement rules

Each measurement uses:
- `value`: finite number or `null`; never substitute zero for a missing sensor reading.
- `unit`: explicit string. Suggested units are `%`, `°C`, `pH`, and `mS/cm`; the API does not convert units.
- `status`: `valid`, `invalid`, or `unavailable`.
- `calibrated`: `true`, `false`, or `null`; do not mark true unless the sensor calibration process has actually been completed.
- `observed_at`: optional timezone-aware timestamp.

The robot agent must document the exact sensor model, raw output, conversion, units, and calibration method before real readings are marked calibrated. The backend does not currently infer NPK or diagnose fertility from pH/moisture/temperature/EC.

## Read data

- `GET /api/v1/scans?limit=50&offset=0` — newest-first history; response keys: `items`, `total`, `limit`, `offset`.
- `GET /api/v1/scans/{id}` — stored scan.
- `GET /api/v1/scans/{id}/analysis` — measurement findings, warnings, quality status, and crop recommendation status.
- `GET /api/v1/weather?latitude={lat}&longitude={lon}` — current weather; check the returned availability/staleness fields before displaying it.

Use `id` as the stable scan identifier. Handle HTTP `404` for missing scans, HTTP `422` for invalid payloads, HTTP `409` for idempotency-key conflicts, and weather responses that explicitly report unavailable data. Do not present simulated readings as physical measurements.

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

Docker Compose is also available from the repository root with `docker compose up --build`.
