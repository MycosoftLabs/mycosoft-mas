"""
Tests for NatureOS MATLAB voice tool handlers.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

pytest.importorskip("httpx")


@pytest.fixture
def client():
    from mycosoft_mas.core.myca_main import app
    return TestClient(app)


@pytest.mark.asyncio
async def test_natureos_anomaly_scan_tool():
    with patch("mycosoft_mas.integrations.natureos_client.NATUREOSClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.run_anomaly_detection = AsyncMock(
            return_value={"anomalies": [], "scores": [0.1]}
        )
        mock_cls.return_value = mock_instance

        from mycosoft_mas.core.routers.voice_tools_api import _run_natureos_matlab_tool
        result = await _run_natureos_matlab_tool("natureos.anomaly_scan", "check for anomalies")
        assert result.success is True
        assert "anomaly" in result.result.lower()


@pytest.mark.asyncio
async def test_natureos_forecast_tool():
    with patch("mycosoft_mas.integrations.natureos_client.NATUREOSClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.forecast_environmental = AsyncMock(
            return_value={"forecast": [22.0, 22.5], "horizonHours": 24}
        )
        mock_cls.return_value = mock_instance

        from mycosoft_mas.core.routers.voice_tools_api import _run_natureos_matlab_tool
        result = await _run_natureos_matlab_tool(
            "natureos.forecast", "predict temperature for next 24 hours"
        )
        assert result.success is True
