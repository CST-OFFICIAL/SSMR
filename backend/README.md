# Smart Soil Monitoring Robot — Backend

FastAPI backend for validated soil-scan ingestion, SQLite persistence, data-quality reporting, weather lookup, and explainable analysis.

## Status

The backend MVP, batch scan ingestion, expanded tests, CI, Docker setup, and integration documentation are merged into `main`. GitHub Actions run 27 completed successfully, including the backend test suite and Docker image build. Crop suitability recommendations remain disabled unless documented, applicable agricultural reference data and decision rules are supplied.

## Run with Python

Use Python 3.11 or newer.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Run these commands from the `backend/` directory. API docs are available at `http://127.0.0.1:8000/docs`.

## Run with Docker Compose

From the repository root:

```bash
docker compose up --build
```

The backend will be available at `http://127.0.0.1:8000`. SQLite data persists in the `ssmr_data` named volume.

See [API contract](docs/API.md) and [cross-agent integration contract](docs/INTEGRATION_CONTRACT.md). Physical sensor integration and the frontend are owned by the other agents.
