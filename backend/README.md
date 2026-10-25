# Smart Soil Monitoring Robot — Backend

FastAPI backend for validated soil-scan ingestion, SQLite persistence, data-quality reporting, and explainable analysis.

## Status

This backend is being built incrementally. The initial implementation will support laptop-only development and clearly labelled simulated readings. Crop suitability recommendations will remain explicitly unavailable until documented, applicable agricultural reference data and decision rules are supplied.

## Development

Use Python 3.11 or newer. Create a virtual environment, install `requirements.txt`, then run `uvicorn app.main:app --reload` from this directory. API documentation is available at `/docs` while the server is running.

See `docs/API.md` for the current API contract. Physical sensor integration and the frontend are owned by other agents.
