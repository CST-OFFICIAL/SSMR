# Smart Soil Monitoring Robot (SSMR)

SSMR is a prototype intended to collect soil measurements, report data quality, and expose analysis through a dashboard. Hardware, backend, and frontend work are developed separately and integrated through pull requests.

## Project status

**Prototype / in development.** The backend MVP was merged via [PR #1](https://github.com/CST-OFFICIAL/SSMR/pull/1). Batch scan ingestion, expanded tests, CI, and Docker setup were merged via [PR #4](https://github.com/CST-OFFICIAL/SSMR/pull/4). Safe retries for buffered batch uploads were added in [PR #5](https://github.com/CST-OFFICIAL/SSMR/pull/5). GitHub Actions runs 27 and 31 completed successfully, each including the backend test suite and Docker image build.

- Backend: FastAPI, SQLite persistence, measurement-quality analysis, weather lookup, configurable cited crop rules, batch ingestion, and optional idempotency keys for batch retries.
- Robot/hardware: Raspberry Pi sensor readers, calibration, and robot movement are separate work and are not claimed as integrated yet.
- Frontend: dashboard is separate and should use `backend/docs/INTEGRATION_CONTRACT.md` as the current hand-off contract.

## Run backend locally with Python

Requires Python 3.11 or newer.

```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

## Run with Docker Compose

From the repository root, with Docker Desktop or Docker Engine plus Compose installed:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000/docs`. SQLite data is stored in the named volume `ssmr_data`. Stop the service with Ctrl+C; use `docker compose down` to remove containers (the named data volume remains unless explicitly removed).

## API endpoints

- `GET /health`
- `POST /api/v1/scans` — submit one scan
- `POST /api/v1/scans/batch` — atomically submit 1–50 buffered scans; optionally send `Idempotency-Key`
- `GET /api/v1/scans?limit=50&offset=0`
- `GET /api/v1/scans/{scan_id}`
- `GET /api/v1/scans/{scan_id}/analysis`
- `GET /api/v1/weather?latitude={lat}&longitude={lon}`

See [API reference](backend/docs/API.md) and [cross-agent integration contract](backend/docs/INTEGRATION_CONTRACT.md).

## Important data limitations

- Missing readings remain unavailable; they are never silently converted to zero.
- Simulated data must not be presented as physical sensor output.
- Sensor readings must not be marked calibrated until calibration has actually been performed.
- The backend does not infer nitrogen, phosphorus, potassium, or yield from pH, moisture, temperature, or electrical conductivity.
- Crop recommendations are disabled until applicable, reviewed, cited crop rules are configured.
- Weather data may be unavailable or stale; consumers should display that status.
- Batch retries are deduplicated only when the caller sends the same `Idempotency-Key` with the same payload. Reusing a key with different content returns HTTP `409`.

## Branch and integration workflow

Work in a feature/agent branch, commit changes there, and open a pull request into `main`. Keep `main` as the reviewed integration branch. Do not merge until relevant checks pass and the cross-agent API/data contract is compatible.
