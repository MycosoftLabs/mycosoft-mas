"""
IBM Quantum Client

Provides access to IBM Quantum services:
- List backends (real quantum hardware + simulators)
- Submit circuits / transpile
- Job management (submit, status, results)
- Qiskit Runtime primitives (Sampler, Estimator)

Uses the IBM Quantum Platform REST API directly (no local qiskit install required).

Env vars:
    IBM_QUANTUM_TOKEN  -- IBM Quantum API token (from quantum.ibm.com)
    IBM_QUANTUM_URL    -- (optional) custom hub URL
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

IBM_Q_BASE = "https://api.quantum-computing.ibm.com/runtime"
IBM_Q_AUTH = "https://auth.quantum-computing.ibm.com/api"


class IbmQuantumClient:
    """Client for IBM Quantum Platform REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get("ibm_quantum_token") or os.getenv("IBM_QUANTUM_TOKEN", "")
        self.base_url = self.config.get("ibm_quantum_url") or os.getenv(
            "IBM_QUANTUM_URL", IBM_Q_BASE
        )
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _auth_headers(self) -> Dict[str, str]:
        if not self._access_token:
            await self._authenticate()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _authenticate(self) -> None:
        """Exchange API token for access token."""
        c = await self._http()
        r = await c.post(
            f"{IBM_Q_AUTH}/users/loginWithToken",
            json={"apiToken": self.token},
        )
        r.raise_for_status()
        self._access_token = r.json().get("id")

    async def health_check(self) -> Dict[str, Any]:
        try:
            backends = await self.list_backends()
            return {
                "status": "ok",
                "backend_count": len(backends) if isinstance(backends, list) else 0,
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def list_backends(self) -> List[Dict[str, Any]]:
        """List available quantum backends."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.get(f"{self.base_url}/backends", headers=headers)
        r.raise_for_status()
        return r.json()

    async def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Get status of a specific backend."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.get(f"{self.base_url}/backends/{backend_name}/status", headers=headers)
        r.raise_for_status()
        return r.json()

    async def backend_properties(self, backend_name: str) -> Dict[str, Any]:
        """Get calibration properties for a backend."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.get(f"{self.base_url}/backends/{backend_name}/properties", headers=headers)
        r.raise_for_status()
        return r.json()

    async def submit_job(
        self,
        program_id: str = "sampler",
        backend: str = "ibmq_qasm_simulator",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit a Qiskit Runtime job."""
        c = await self._http()
        headers = await self._auth_headers()
        body = {
            "program_id": program_id,
            "backend": backend,
            "params": params or {},
        }
        r = await c.post(f"{self.base_url}/jobs", headers=headers, json=body)
        r.raise_for_status()
        return r.json()

    async def job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.get(f"{self.base_url}/jobs/{job_id}", headers=headers)
        r.raise_for_status()
        return r.json()

    async def job_results(self, job_id: str) -> Dict[str, Any]:
        """Get job results."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.get(f"{self.base_url}/jobs/{job_id}/results", headers=headers)
        r.raise_for_status()
        return r.json()

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        c = await self._http()
        headers = await self._auth_headers()
        r = await c.post(f"{self.base_url}/jobs/{job_id}/cancel", headers=headers)
        r.raise_for_status()
        return r.json()

    async def list_jobs(self, limit: int = 20, pending: bool = False) -> List[Dict[str, Any]]:
        """List recent jobs."""
        c = await self._http()
        headers = await self._auth_headers()
        params: Dict[str, Any] = {"limit": limit}
        if pending:
            params["pending"] = "true"
        r = await c.get(f"{self.base_url}/jobs", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
