from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _parse_upstream_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


async def get_weather(latitude: float, longitude: float, *, client: Any = httpx.AsyncClient) -> dict[str, Any]:
    """Fetch current Open-Meteo conditions. Failures return unavailable, never fake weather."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "timezone": "UTC",
        "forecast_days": 1,
    }
    try:
        async with client(timeout=5.0) as session:
            response = await session.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, TimeoutError, OSError, ValueError):
        return {
            "status": "unavailable",
            "provider": "Open-Meteo",
            "current": None,
            "observed_at": None,
            "stale": None,
            "warning": "Weather service could not be reached; no weather values are available.",
        }

    current = payload.get("current")
    if not isinstance(current, dict):
        return {
            "status": "unavailable", "provider": "Open-Meteo", "current": None,
            "observed_at": None, "stale": None,
            "warning": "Weather provider returned no current conditions.",
        }
    observed_at = _parse_upstream_time(current.get("time"))
    if observed_at is None:
        return {
            "status": "unavailable", "provider": "Open-Meteo", "current": None,
            "observed_at": None, "stale": None,
            "warning": "Weather provider returned an invalid or timezone-naive timestamp.",
        }
    age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
    stale = age_seconds > 2 * 60 * 60 or age_seconds < -15 * 60
    values = {
        "temperature_2m_c": current.get("temperature_2m"),
        "relative_humidity_2m_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_10m_kmh": current.get("wind_speed_10m"),
    }
    # Reject a structurally empty payload rather than returning a success-shaped object.
    if not any(value is not None for value in values.values()):
        return {
            "status": "unavailable", "provider": "Open-Meteo", "current": None,
            "observed_at": observed_at.isoformat(), "stale": None,
            "warning": "Weather provider returned no usable weather values.",
        }
    return {
        "status": "stale" if stale else "available",
        "provider": "Open-Meteo",
        "current": values,
        "observed_at": observed_at.isoformat(),
        "stale": stale,
        "warning": "Weather timestamp is stale or unexpectedly in the future." if stale else None,
    }
