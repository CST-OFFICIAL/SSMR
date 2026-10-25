from datetime import datetime, timezone

import pytest

from app.weather import get_weather


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *, timeout=5.0, payload=None):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params):
        return FakeResponse(self.payload)


@pytest.mark.asyncio
async def test_weather_rejects_timezone_naive_provider_timestamp():
    payload = {"current": {
        "time": "2026-10-25T09:00:00",
        "temperature_2m": 20,
        "relative_humidity_2m": 60,
        "precipitation": 0,
        "wind_speed_10m": 2,
    }}
    result = await get_weather(26.75, 94.63, client=lambda **kwargs: FakeClient(payload=payload, **kwargs))
    assert result["status"] == "unavailable"
    assert result["current"] is None
    assert result["stale"] is None


@pytest.mark.asyncio
async def test_weather_rejects_empty_current_values():
    payload = {"current": {
        "time": datetime.now(timezone.utc).isoformat(),
        "temperature_2m": None,
        "relative_humidity_2m": None,
        "precipitation": None,
        "wind_speed_10m": None,
    }}
    result = await get_weather(26.75, 94.63, client=lambda **kwargs: FakeClient(payload=payload, **kwargs))
    assert result["status"] == "unavailable"
    assert result["current"] is None
    assert "no usable weather values" in result["warning"]
