"""
Tests for NATUREOSClient (NatureOS MATLAB integration).
"""
import pytest
from unittest.mock import AsyncMock, patch

pytest.importorskip("httpx")


@pytest.fixture
def client():
    from mycosoft_mas.integrations.natureos_client import NATUREOSClient
    return NATUREOSClient(base_url="http://test-natureos:5000", timeout=5)


@pytest.mark.asyncio
async def test_run_anomaly_detection(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"anomalies": [], "scores": [0.1, 0.2]}
        mock_resp.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await client.run_anomaly_detection(device_id="mushroom1")
        assert "anomalies" in result
        assert result["scores"] == [0.1, 0.2]


@pytest.mark.asyncio
async def test_forecast_environmental(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"forecast": [22.1, 22.3], "horizonHours": 24}
        mock_resp.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await client.forecast_environmental(metric="temperature", hours=24)
        assert "forecast" in result
        assert result["horizonHours"] == 24


@pytest.mark.asyncio
async def test_classify_morphology(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"species": "Agaricus", "confidence": 0.85}
        mock_resp.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await client.classify_morphology(signal_vector=[0.1, 0.2, 0.3])
        assert "species" in result


@pytest.mark.asyncio
async def test_get_matlab_health(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"status": "healthy", "engine": "ready"}
        mock_resp.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await client.get_matlab_health()
        assert result["status"] == "healthy"
