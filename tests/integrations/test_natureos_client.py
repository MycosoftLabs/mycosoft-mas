"""
Tests for NATUREOSClient (NatureOS MATLAB integration).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytest.importorskip("httpx")


def _make_mock_client(post_json=None, get_json=None):
    mock_resp = MagicMock()
    mock_resp.json.return_value = get_json if get_json is not None else (post_json or {})
    mock_resp.raise_for_status = MagicMock()

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_resp)
    mock_instance.get = AsyncMock(return_value=mock_resp)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    return mock_instance


@pytest.fixture
def client():
    from mycosoft_mas.integrations.natureos_client import NATUREOSClient
    return NATUREOSClient(base_url="http://test-natureos:5000", timeout=5)


@pytest.mark.asyncio
async def test_run_anomaly_detection(client):
    with patch("mycosoft_mas.integrations.natureos_client.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = _make_mock_client(
            post_json={"anomalies": [], "scores": [0.1, 0.2]}
        )
        result = await client.run_anomaly_detection(device_id="mushroom1")
        assert "anomalies" in result
        assert result["scores"] == [0.1, 0.2]


@pytest.mark.asyncio
async def test_forecast_environmental(client):
    with patch("mycosoft_mas.integrations.natureos_client.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = _make_mock_client(
            post_json={"forecast": [22.1, 22.3], "horizonHours": 24}
        )
        result = await client.forecast_environmental(metric="temperature", hours=24)
        assert "forecast" in result
        assert result["horizonHours"] == 24


@pytest.mark.asyncio
async def test_classify_morphology(client):
    with patch("mycosoft_mas.integrations.natureos_client.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = _make_mock_client(
            post_json={"species": "Agaricus", "confidence": 0.85}
        )
        result = await client.classify_morphology(signal_vector=[0.1, 0.2, 0.3])
        assert "species" in result


@pytest.mark.asyncio
async def test_get_matlab_health(client):
    with patch("mycosoft_mas.integrations.natureos_client.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = _make_mock_client(
            get_json={"status": "healthy", "engine": "ready"}
        )
        result = await client.get_matlab_health()
        assert result["status"] == "healthy"
