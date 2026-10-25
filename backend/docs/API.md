# Backend API contract (v0.1)

Base URL during local development: `http://127.0.0.1:8000`.

## Endpoints

- `GET /health` — process health check.
- `POST /api/v1/scans` — validate and persist one soil scan; returns `201` and the scan with generated `id` and `received_at`.
- `GET /api/v1/weather?latitude=26.75&longitude=94.63` — fetch current conditions from Open-Meteo; reports `available`, `stale`, or `unavailable` and never fabricates values.
- `GET /api/v1/scans?limit=50&offset=0` — newest-first scan history with `items`, `total`, `limit`, and `offset`.
- `GET /api/v1/scans/{scan_id}` — one stored scan, or `404`.
- `GET /api/v1/scans/{scan_id}/analysis` — data-quality findings and limitations, or `404`.

Interactive OpenAPI documentation is served at `/docs` when the app is running.

## Scan payload

`source` is required and must be `simulated` or `physical`. `timestamp` must be ISO 8601 with timezone information. `location` is optional and contains latitude and longitude. The four measurement objects are `soil_moisture`, `soil_temperature`, `ph`, and `ec`; each has `value` (nullable number), `unit`, `status` (`valid`, `invalid`, or `unavailable`), `calibrated` (nullable boolean), and optional timezone-aware `observed_at`. Missing measurement objects default to unavailable, not zero. Unknown fields are rejected.

Suggested units are `%`, `°C`, `pH`, and `mS/cm`; the API records the supplied unit and does not silently convert it. The robot agent must confirm exact sensor output units before hardware integration.

## Analysis limitations

Analysis currently evaluates availability/status/calibration flags and emits warnings. It does not diagnose soil fertility or infer nitrogen, phosphorus, potassium, or yield. Crop recommendations are intentionally withheld until the project has reviewed, documented crop/region/season-specific reference data and validated rules.

## Configuration

- `SSMR_DATABASE_PATH` — optional SQLite file path. Defaults to `backend/data/soil_scans.sqlite3`.
- Weather requests use a 5-second timeout. `stale` is true when the provider timestamp is more than two hours old or more than 15 minutes in the future. A failed request returns an explicit unavailable response.
- `SSMR_CORS_ORIGINS` — comma-separated browser origins. Defaults to local Vite origins `http://localhost:5173,http://127.0.0.1:5173`.

No API keys are required for the current implementation. SQLite is intended for the prototype; back up the database file if the records matter.

## Run locally

```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests from `backend/` with `pytest -q`.
