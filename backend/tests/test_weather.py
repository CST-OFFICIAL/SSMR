from datetime import datetime, timezone

import httpx
import pytest

from app.weather import get_weather

class FakeClient:
    def __init__(self, *, timeout=5.0, payload=None, error=None):
        self.payload = payload
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params):
        if self.error:
            raise self.error
        return FakeResponse(self.payload)

class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

@pytest.mark.asyncio
async def test_weather_success_with_recent_timestamp():
    stamp = datetime.now(timezone.utc).isoformat()
    payload = {"current": {"time": stamp, "temperature_2m": 22.1, "relative_humidity_2m": 61, "precipitation": 0, "wind_speed_10m": 4}}
    result = await get_weather(26.75, 94.63, client=lambda **kwargs: FakeClient(payload=payload, **kwargs))
    assert result["status"] == "available"
    assert result["current"]["temperature_2m_c"] == 22.1
    assert result["stale"] is False

@pytest.mark.asyncio
async def test_weather_network_failure_is_explicitly_unavailable():
    result = await get_weather(26.75, 94.63, client=lambda **kwargs: FakeClient(error=httpx.ConnectError("offline"), **kwargs))
    assert result["status"] == "unavailable"
    assert result["current"] is None
    assert result["stale"] is None
