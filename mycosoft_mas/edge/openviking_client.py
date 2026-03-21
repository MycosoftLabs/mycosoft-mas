"""
OpenViking HTTP Client for MAS.

Low-level async HTTP client for communicating with OpenViking context database
servers running on edge devices (Jetson Orin). Supports all OpenViking API
operations: filesystem navigation, search, ingestion, and session management.

OpenViking runs on port 1933 by default and exposes a REST API for managing
the viking:// context filesystem.

Created: March 19, 2026
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

OPENVIKING_DEFAULT_PORT = 1933
DEFAULT_TIMEOUT = 30.0


class OpenVikingClient:
    """HTTP client for an OpenViking context database server."""

    def __init__(
        self,
        host: str,
        port: int = OPENVIKING_DEFAULT_PORT,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self._base_url = base_url or f"http://{host}:{port}"
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout)
        self._connected = False
        self._client: Optional[httpx.AsyncClient] = None
        self._server_info: Dict[str, Any] = {}

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                base_url=self._base_url,
                headers=self._headers(),
            )
        return self._client

    async def connect(self) -> bool:
        """Verify OpenViking server is reachable and get server info."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(
                    f"{self._base_url}/health",
                    headers=self._headers(),
                )
                r.raise_for_status()
                data = r.json()
                self._server_info = data
                self._connected = True
                self._client = httpx.AsyncClient(
                    timeout=self._timeout,
                    base_url=self._base_url,
                    headers=self._headers(),
                )
                logger.info("Connected to OpenViking at %s:%d", self.host, self.port)
                return True
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("OpenViking connection failed (%s:%d): %s", self.host, self.port, e)
            self._connected = False
            return False
        except Exception as e:
            logger.exception("OpenViking connect error: %s", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Filesystem Operations ──────────────────────────────────────────

    async def ls(self, uri: str = "viking://") -> Optional[List[Dict[str, Any]]]:
        """List contents of a viking:// directory."""
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/ls", json={"uri": uri})
            r.raise_for_status()
            return r.json().get("entries", [])
        except Exception as e:
            logger.warning("OpenViking ls(%s) failed: %s", uri, e)
            return None

    async def tree(self, uri: str = "viking://", depth: int = 3) -> Optional[Dict[str, Any]]:
        """Get tree structure of a viking:// path."""
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/tree", json={"uri": uri, "depth": depth})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("OpenViking tree(%s) failed: %s", uri, e)
            return None

    async def read(self, uri: str, tier: str = "L2") -> Optional[Dict[str, Any]]:
        """Read content at a viking:// path with specified tier (L0/L1/L2).

        L0 = ~100 token abstract, L1 = ~2k token overview, L2 = full content.
        """
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/read", json={"uri": uri, "tier": tier})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("OpenViking read(%s, tier=%s) failed: %s", uri, tier, e)
            return None

    async def abstract(self, uri: str) -> Optional[str]:
        """Get L0 abstract (~100 tokens) for a viking:// path."""
        result = await self.read(uri, tier="L0")
        if result:
            return result.get("content", "")
        return None

    async def overview(self, uri: str) -> Optional[str]:
        """Get L1 overview (~2k tokens) for a viking:// path."""
        result = await self.read(uri, tier="L1")
        if result:
            return result.get("content", "")
        return None

    async def mkdir(self, uri: str) -> bool:
        """Create a directory at a viking:// path."""
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/mkdir", json={"uri": uri})
            r.raise_for_status()
            return True
        except Exception as e:
            logger.warning("OpenViking mkdir(%s) failed: %s", uri, e)
            return False

    async def write_content(
        self,
        uri: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Write content to a viking:// path."""
        try:
            client = self._client_or_raise()
            body: Dict[str, Any] = {"uri": uri, "content": content}
            if metadata:
                body["metadata"] = metadata
            r = await client.post("/api/v1/fs/write", json=body)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.warning("OpenViking write(%s) failed: %s", uri, e)
            return False

    async def delete(self, uri: str) -> bool:
        """Delete content at a viking:// path."""
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/delete", json={"uri": uri})
            r.raise_for_status()
            return True
        except Exception as e:
            logger.warning("OpenViking delete(%s) failed: %s", uri, e)
            return False

    async def glob(self, pattern: str) -> Optional[List[str]]:
        """Glob match files in the viking:// filesystem."""
        try:
            client = self._client_or_raise()
            r = await client.post("/api/v1/fs/glob", json={"pattern": pattern})
            r.raise_for_status()
            return r.json().get("matches", [])
        except Exception as e:
            logger.warning("OpenViking glob(%s) failed: %s", pattern, e)
            return None

    # ── Search Operations ──────────────────────────────────────────────

    async def find(
        self,
        query: str,
        top_k: int = 10,
        target_uri: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Semantic search across the context database.

        Uses OpenViking's Directory Recursive Retrieval algorithm:
        1. Intent analysis (VLM expands query)
        2. Vector search on L0 abstracts
        3. Refined exploration via L1 overviews
        4. Recursive drill-down with hierarchical scoring
        """
        try:
            client = self._client_or_raise()
            body: Dict[str, Any] = {"query": query, "top_k": top_k}
            if target_uri:
                body["target_uri"] = target_uri
            r = await client.post("/api/v1/search/find", json=body)
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.warning("OpenViking find(%s) failed: %s", query, e)
            return None

    async def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """High-level search with default parameters."""
        return await self.find(query, top_k=10)

    async def grep(
        self,
        pattern: str,
        target_uri: str = "viking://",
    ) -> Optional[List[Dict[str, Any]]]:
        """Pattern match search within viking:// filesystem."""
        try:
            client = self._client_or_raise()
            r = await client.post(
                "/api/v1/search/grep",
                json={"pattern": pattern, "target_uri": target_uri},
            )
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.warning("OpenViking grep(%s) failed: %s", pattern, e)
            return None

    # ── Ingestion ──────────────────────────────────────────────────────

    async def add_resource(
        self,
        content: str,
        reason: str,
        target: str = "viking://resources/",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Ingest content into the context database.

        OpenViking will asynchronously generate L0/L1 summaries via VLM.
        Returns the URI of the created resource.
        """
        try:
            client = self._client_or_raise()
            body: Dict[str, Any] = {
                "content": content,
                "reason": reason,
                "target": target,
            }
            if metadata:
                body["metadata"] = metadata
            r = await client.post("/api/v1/ingest/add", json=body)
            r.raise_for_status()
            return r.json().get("uri")
        except Exception as e:
            logger.warning("OpenViking add_resource failed: %s", e)
            return None

    async def wait_processed(self, timeout: float = 60.0) -> bool:
        """Wait until all pending ingestion tasks are processed."""
        try:
            client = self._client_or_raise()
            r = await client.post(
                "/api/v1/ingest/wait",
                json={"timeout": timeout},
                timeout=httpx.Timeout(timeout + 10),
            )
            r.raise_for_status()
            return r.json().get("processed", False)
        except Exception as e:
            logger.warning("OpenViking wait_processed failed: %s", e)
            return False

    # ── Session Management ─────────────────────────────────────────────

    async def create_session(
        self,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create or resume a session for conversation tracking."""
        try:
            client = self._client_or_raise()
            body: Dict[str, Any] = {}
            if session_id:
                body["session_id"] = session_id
            r = await client.post("/api/v1/session/create", json=body)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("OpenViking create_session failed: %s", e)
            return None

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> bool:
        """Add a message to a session."""
        try:
            client = self._client_or_raise()
            r = await client.post(
                "/api/v1/session/message",
                json={
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                },
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.warning("OpenViking add_message failed: %s", e)
            return False

    # ── Health & Info ──────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Full health check with server info."""
        try:
            client = self._client_or_raise()
            r = await client.get("/health")
            r.raise_for_status()
            data = r.json()
            data["reachable"] = True
            return data
        except Exception as e:
            return {
                "status": "unhealthy",
                "reachable": False,
                "error": str(e),
                "host": self.host,
                "port": self.port,
            }

    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get storage and index statistics."""
        try:
            client = self._client_or_raise()
            r = await client.get("/api/v1/stats")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("OpenViking get_stats failed: %s", e)
            return None

    async def list_changed_since(
        self,
        uri: str,
        since: datetime,
    ) -> Optional[List[Dict[str, Any]]]:
        """List items under a URI that changed since a given timestamp.

        Used by the sync bridge to detect new/updated content on devices.
        """
        try:
            client = self._client_or_raise()
            r = await client.post(
                "/api/v1/fs/changes",
                json={
                    "uri": uri,
                    "since": since.isoformat(),
                },
            )
            r.raise_for_status()
            return r.json().get("entries", [])
        except Exception as e:
            logger.warning("OpenViking list_changed_since(%s) failed: %s", uri, e)
            return None
