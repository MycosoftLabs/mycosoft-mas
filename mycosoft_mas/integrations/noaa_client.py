"""
NOAA Full Suite Client

Comprehensive access to NOAA data services:
- Climate Data Online (CDO/NCEI) -- historical climate records
- National Weather Service (NWS) -- forecasts, alerts, observations
- NDBC Buoy Data -- real-time ocean observations
- Tides & Currents (CO-OPS) -- tide predictions, water levels
- Coral Reef Watch -- bleaching alerts, sea surface temperature
- NOAA Fisheries -- stock assessments, catch data

Env vars:
    NOAA_CDO_TOKEN   -- token for Climate Data Online (ncdc.noaa.gov/cdo-web/token)
    NOAA_API_KEY     -- alias (falls back to CDO token)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

CDO_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
NWS_BASE = "https://api.weather.gov"
NDBC_BASE = "https://www.ndbc.noaa.gov"
COOPS_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
COOPS_META = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
CORAL_BASE = "https://coralreefwatch.noaa.gov/product/vs/data"
FISHERIES_BASE = "https://apps-st.fisheries.noaa.gov/ods/foss"


class NoaaClient:
    """Unified NOAA data client covering climate, weather, ocean, and fisheries."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cdo_token = (
            self.config.get("cdo_token")
            or os.getenv("NOAA_CDO_TOKEN", "")
            or os.getenv("NOAA_API_KEY", "")
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        try:
            c = await self._http()
            nws = await c.get(f"{NWS_BASE}/alerts/active/count")
            return {
                "status": "ok" if nws.status_code == 200 else "degraded",
                "nws_alerts": nws.status_code == 200,
                "cdo_token_set": bool(self.cdo_token),
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # -- Climate Data Online (CDO / NCEI) ------------------------------------

    async def cdo_datasets(self, limit: int = 25) -> Dict[str, Any]:
        """List available CDO datasets (GHCND, GSOM, GSOY, etc.)."""
        c = await self._http()
        r = await c.get(
            f"{CDO_BASE}/datasets",
            headers={"token": self.cdo_token},
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()

    async def cdo_data(
        self,
        dataset_id: str = "GHCND",
        datatype_id: Optional[str] = None,
        location_id: Optional[str] = None,
        station_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 1,
    ) -> Dict[str, Any]:
        """Fetch climate observations from CDO."""
        c = await self._http()
        params: Dict[str, Any] = {
            "datasetid": dataset_id,
            "limit": limit,
            "offset": offset,
        }
        if datatype_id:
            params["datatypeid"] = datatype_id
        if location_id:
            params["locationid"] = location_id
        if station_id:
            params["stationid"] = station_id
        if start_date:
            params["startdate"] = start_date
        if end_date:
            params["enddate"] = end_date
        r = await c.get(
            f"{CDO_BASE}/data",
            headers={"token": self.cdo_token},
            params=params,
        )
        r.raise_for_status()
        return r.json()

    async def cdo_stations(
        self,
        dataset_id: str = "GHCND",
        location_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List CDO weather stations."""
        c = await self._http()
        params: Dict[str, Any] = {"datasetid": dataset_id, "limit": limit}
        if location_id:
            params["locationid"] = location_id
        r = await c.get(
            f"{CDO_BASE}/stations",
            headers={"token": self.cdo_token},
            params=params,
        )
        r.raise_for_status()
        return r.json()

    # -- National Weather Service (NWS) --------------------------------------

    async def nws_alerts(
        self,
        area: Optional[str] = None,
        event: Optional[str] = None,
        urgency: Optional[str] = None,
        severity: Optional[str] = None,
        status: str = "actual",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get active NWS weather alerts."""
        c = await self._http()
        params: Dict[str, Any] = {"status": status, "limit": limit}
        if area:
            params["area"] = area
        if event:
            params["event"] = event
        if urgency:
            params["urgency"] = urgency
        if severity:
            params["severity"] = severity
        r = await c.get(f"{NWS_BASE}/alerts/active", params=params)
        r.raise_for_status()
        return r.json()

    async def nws_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get 7-day forecast for a lat/lon (two-step: points -> forecast)."""
        c = await self._http()
        pts = await c.get(f"{NWS_BASE}/points/{lat},{lon}")
        pts.raise_for_status()
        forecast_url = pts.json()["properties"]["forecast"]
        fc = await c.get(forecast_url)
        fc.raise_for_status()
        return fc.json()

    async def nws_forecast_hourly(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get hourly forecast for a lat/lon."""
        c = await self._http()
        pts = await c.get(f"{NWS_BASE}/points/{lat},{lon}")
        pts.raise_for_status()
        url = pts.json()["properties"]["forecastHourly"]
        fc = await c.get(url)
        fc.raise_for_status()
        return fc.json()

    async def nws_observations(self, station_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get latest observations from an NWS station (e.g. KJFK)."""
        c = await self._http()
        r = await c.get(
            f"{NWS_BASE}/stations/{station_id}/observations",
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()

    # -- NDBC Buoy Data -------------------------------------------------------

    async def ndbc_latest(self, station_id: str) -> str:
        """Get latest standard meteorological data for a buoy station (text)."""
        c = await self._http()
        r = await c.get(f"{NDBC_BASE}/data/realtime2/{station_id}.txt")
        r.raise_for_status()
        return r.text

    async def ndbc_spectral(self, station_id: str) -> str:
        """Get spectral wave summary for a buoy station."""
        c = await self._http()
        r = await c.get(f"{NDBC_BASE}/data/realtime2/{station_id}.spec")
        r.raise_for_status()
        return r.text

    async def ndbc_ocean(self, station_id: str) -> str:
        """Get oceanographic data (SST, salinity, O2, pH)."""
        c = await self._http()
        r = await c.get(f"{NDBC_BASE}/data/realtime2/{station_id}.ocean")
        r.raise_for_status()
        return r.text

    async def ndbc_active_stations(self) -> str:
        """List all active NDBC stations (XML)."""
        c = await self._http()
        r = await c.get(f"{NDBC_BASE}/activestations.xml")
        r.raise_for_status()
        return r.text

    # -- Tides & Currents (CO-OPS) -------------------------------------------

    async def tide_predictions(
        self,
        station: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        datum: str = "MLLW",
    ) -> Dict[str, Any]:
        """Get tide predictions for a CO-OPS station."""
        c = await self._http()
        today = datetime.utcnow().strftime("%Y%m%d")
        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y%m%d")
        params = {
            "product": "predictions",
            "application": "Mycosoft_MAS",
            "station": station,
            "begin_date": begin_date or today,
            "end_date": end_date or tomorrow,
            "datum": datum,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
        }
        r = await c.get(COOPS_BASE, params=params)
        r.raise_for_status()
        return r.json()

    async def water_levels(
        self,
        station: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get observed water levels."""
        c = await self._http()
        today = datetime.utcnow().strftime("%Y%m%d")
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
        params = {
            "product": "water_level",
            "application": "Mycosoft_MAS",
            "station": station,
            "begin_date": begin_date or yesterday,
            "end_date": end_date or today,
            "datum": "MLLW",
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
        }
        r = await c.get(COOPS_BASE, params=params)
        r.raise_for_status()
        return r.json()

    async def water_temperature(
        self,
        station: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get water temperature observations."""
        c = await self._http()
        today = datetime.utcnow().strftime("%Y%m%d")
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
        params = {
            "product": "water_temperature",
            "application": "Mycosoft_MAS",
            "station": station,
            "begin_date": begin_date or yesterday,
            "end_date": end_date or today,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
        }
        r = await c.get(COOPS_BASE, params=params)
        r.raise_for_status()
        return r.json()

    async def currents(
        self,
        station: str,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get current (velocity/direction) observations."""
        c = await self._http()
        today = datetime.utcnow().strftime("%Y%m%d")
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
        params = {
            "product": "currents",
            "application": "Mycosoft_MAS",
            "station": station,
            "begin_date": begin_date or yesterday,
            "end_date": end_date or today,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
        }
        r = await c.get(COOPS_BASE, params=params)
        r.raise_for_status()
        return r.json()

    async def coops_stations(self, station_type: str = "tidepredictions") -> Dict[str, Any]:
        """List CO-OPS stations."""
        c = await self._http()
        r = await c.get(
            f"{COOPS_META}/stations.json",
            params={"type": station_type, "units": "metric"},
        )
        r.raise_for_status()
        return r.json()

    # -- Coral Reef Watch -----------------------------------------------------

    async def coral_bleaching_alert(self, region: str = "global") -> str:
        """Get coral bleaching heat-stress alert area (CSV)."""
        c = await self._http()
        r = await c.get(
            f"https://coralreefwatch.noaa.gov/product/vs/data/vs_main_{region}.txt"
        )
        r.raise_for_status()
        return r.text

    async def coral_sst_anomaly(self) -> str:
        """Get global SST anomaly product (text)."""
        c = await self._http()
        r = await c.get(
            "https://coralreefwatch.noaa.gov/product/vs/data/vs_main_global.txt"
        )
        r.raise_for_status()
        return r.text

    # -- NOAA Fisheries -------------------------------------------------------

    async def fisheries_landings(
        self,
        year: Optional[int] = None,
        state: Optional[str] = None,
        species: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query NOAA Fisheries commercial landings via FOSS."""
        c = await self._http()
        params: Dict[str, Any] = {"fmt": "json", "top": limit}
        if year:
            params["year"] = year
        if state:
            params["state"] = state
        if species:
            params["tsn"] = species
        r = await c.get(f"{FISHERIES_BASE}/landings", params=params)
        r.raise_for_status()
        return r.json()

    async def fisheries_trade(
        self,
        year: Optional[int] = None,
        product: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query NOAA Fisheries foreign trade data."""
        c = await self._http()
        params: Dict[str, Any] = {"fmt": "json", "top": limit}
        if year:
            params["year"] = year
        if product:
            params["product"] = product
        r = await c.get(f"{FISHERIES_BASE}/trade", params=params)
        r.raise_for_status()
        return r.json()

    # -- Cleanup --------------------------------------------------------------

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
