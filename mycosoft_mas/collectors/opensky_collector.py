"""
OpenSky Collector - February 6, 2026

Collects aircraft data from OpenSky Network.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class OpenSkyCollector(BaseCollector):
    """
    Collects live aircraft positions from OpenSky Network.

    API: https://opensky-network.org/apidoc/rest.html
    """

    name = "opensky"
    entity_type = "aircraft"
    poll_interval_seconds = 10  # Free tier rate limit

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__()
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")
        # OAuth2 client-credentials (OpenSky deprecated basic auth) — takes precedence.
        self.client_id = os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = os.getenv("OPENSKY_CLIENT_SECRET")
        self._oauth_token: Optional[str] = None
        self._oauth_expires_at: float = 0.0
        self.base_url = "https://opensky-network.org/api"
        self._session: Optional[aiohttp.ClientSession] = None
        # Env-tunable so ops can stay within OpenSky's daily credit budget without a redeploy.
        self.poll_interval_seconds = int(
            os.getenv("OPENSKY_POLL_SECONDS", str(self.poll_interval_seconds))
        )

        # Bounding box for queries (can be configured)
        self.bbox: Optional[tuple] = None  # (lamin, lamax, lomin, lomax)

    async def initialize(self) -> None:
        # OAuth2 client-credentials takes precedence; only fall back to legacy basic
        # auth when no OAuth creds are configured (OpenSky deprecated basic auth).
        auth = None
        if not (self.client_id and self.client_secret) and self.username and self.password:
            auth = aiohttp.BasicAuth(self.username, self.password)

        self._session = aiohttp.ClientSession(auth=auth)

    async def _get_oauth_bearer(self) -> Optional[str]:
        """Fetch + cache an OpenSky OAuth2 client-credentials bearer token."""
        if not (self.client_id and self.client_secret):
            return None
        now = time.time()
        if self._oauth_token and now < self._oauth_expires_at:
            return self._oauth_token
        token_url = (
            "https://auth.opensky-network.org/auth/realms/"
            "opensky-network/protocol/openid-connect/token"
        )
        try:
            async with self._session.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            ) as resp:
                if resp.status != 200:
                    logger.error("OpenSky OAuth token HTTP %s", resp.status)
                    return None
                payload = await resp.json()
        except Exception as exc:
            logger.error("OpenSky OAuth token error: %s", exc)
            return None
        token = payload.get("access_token")
        if not token:
            return None
        ttl = float(payload.get("expires_in") or 1800)
        self._oauth_token = token
        # Refresh 60s early to avoid edge-of-expiry 401s.
        self._oauth_expires_at = now + max(60.0, ttl - 60.0)
        return token

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch aircraft states from OpenSky."""
        if not self._session:
            await self.initialize()

        url = f"{self.base_url}/states/all"
        params = {}

        if self.bbox:
            params["lamin"] = self.bbox[0]
            params["lamax"] = self.bbox[1]
            params["lomin"] = self.bbox[2]
            params["lomax"] = self.bbox[3]

        headers = {"Accept": "application/json"}
        bearer = await self._get_oauth_bearer()
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        try:
            async with self._session.get(
                url, params=params, headers=headers, timeout=30
            ) as resp:
                if resp.status == 429:
                    logger.warning("OpenSky rate limited")
                    await asyncio.sleep(60)
                    return []

                if resp.status != 200:
                    logger.error(f"OpenSky error: {resp.status}")
                    return []

                data = await resp.json()

                events = []
                states = data.get("states", []) or []
                max_aircraft = int(os.getenv("OPENSKY_MAX_AIRCRAFT", "500"))
                if len(states) > max_aircraft:
                    states = states[:max_aircraft]

                for state in states:
                    if state[5] is None or state[6] is None:
                        continue  # Skip without position

                    events.append(
                        RawEvent(
                            source="opensky",
                            entity_id=state[0] or str(uuid.uuid4()),  # ICAO24
                            entity_type="aircraft",
                            timestamp=datetime.utcfromtimestamp(
                                data.get("time", datetime.utcnow().timestamp())
                            ),
                            data={
                                "icao24": state[0],
                                "callsign": (state[1] or "").strip(),
                                "origin_country": state[2],
                                "time_position": state[3],
                                "last_contact": state[4],
                                "lng": state[5],
                                "lat": state[6],
                                "altitude": state[7] or state[13],  # baro_altitude or geo_altitude
                                "on_ground": state[8],
                                "velocity": state[9],
                                "heading": state[10],
                                "vertical_rate": state[11],
                                "squawk": state[14],
                            },
                            raw_data=state,
                        )
                    )

                logger.info(f"OpenSky fetched {len(events)} aircraft")
                return events

        except Exception as e:
            logger.error(f"OpenSky fetch error: {e}")
            raise

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform OpenSky data to timeline event."""
        data = raw.data

        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"opensky:{data['icao24']}")),
            entity_type="aircraft",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=data.get("altitude"),
            properties={
                "icao24": data["icao24"],
                "callsign": data["callsign"],
                "origin_country": data["origin_country"],
                "velocity": data.get("velocity"),
                "heading": data.get("heading"),
                "vertical_rate": data.get("vertical_rate"),
                "on_ground": data.get("on_ground", False),
                "squawk": data.get("squawk"),
            },
            source="opensky",
            quality_score=calculate_quality_score(data, "aircraft", "opensky", raw.timestamp),
        )
