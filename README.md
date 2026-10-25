# Smart Soil Monitoring Robot (SSMR)

SSMR is a prototype project intended to collect soil measurements, report data quality, and present transparent soil analysis through a dashboard. The project is being developed in separate components so hardware, backend, and frontend work can proceed independently.

## Project status

**Prototype / in development.** The backend MVP is on the `agent/backend-analysis` branch and proposed in [Pull Request #1](https://github.com/CST-OFFICIAL/SSMR/pull/1). It has not been merged into `main`. Backend tests have been added, and GitHub Actions is configured to run them on relevant pushes and pull requests; check the Actions tab for the actual run result.

- Backend: FastAPI API, SQLite persistence, measurement-quality analysis, weather lookup, configurable cited crop rules.
- Robot/hardware: Raspberry Pi sensor readers, calibration, and movement are separate work and are not claimed as integrated by the backend.
- Frontend: dashboard work is separate and must use the API contract documented in `backend/docs/INTEGRATION_CONTRACT.md`.

## Backend quick start

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

Then open `http://127.0.0.1:8000/docs`.

## API endpoints

- `GET /health`
- `POST /api/v1/scans`
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

## Branch and integration workflow

Work in a feature/agent branch, commit changes there, and open a pull request into `main`. Keep `main` as the reviewed integration branch. Do not merge until relevant checks pass and the cross-agent API/data contract is compatible.
