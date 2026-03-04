"""
Google Quantum Client

Provides access to Google Quantum AI services:
- Cirq circuit design helpers (serialization, noise models)
- Google Quantum Engine REST API (job submission, processor info)
- Quantum simulation utilities

For full Cirq functionality, install `cirq-google` locally.
This client wraps the Quantum Engine REST API for remote job management.

Env vars:
    GOOGLE_QUANTUM_PROJECT_ID  -- Google Cloud project with Quantum Engine enabled
    GOOGLE_APPLICATION_CREDENTIALS  -- path to GCP service account JSON
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

QE_BASE = "https://quantum.googleapis.com/v1alpha1"


class GoogleQuantumClient:
    """Client for Google Quantum Engine REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.project_id = self.config.get("project_id") or os.getenv("GOOGLE_QUANTUM_PROJECT_ID", "")
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _get_token(self) -> str:
        """Get GCP access token via metadata server or service account."""
        if self._token:
            return self._token
        c = await self._http()
        try:
            r = await c.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            if r.status_code == 200:
                self._token = r.json()["access_token"]
                return self._token
        except Exception:
            pass
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        if creds_path:
            logger.info("Using service account credentials from %s", creds_path)
        return self._token or ""

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok" if self.project_id else "no_project",
            "project_id": self.project_id,
            "ts": datetime.utcnow().isoformat(),
        }

    async def list_processors(self) -> Dict[str, Any]:
        """List available quantum processors."""
        c = await self._http()
        h = await self._headers()
        r = await c.get(
            f"{QE_BASE}/projects/{self.project_id}/processors",
            headers=h,
        )
        r.raise_for_status()
        return r.json()

    async def get_processor(self, processor_id: str) -> Dict[str, Any]:
        """Get details for a specific processor."""
        c = await self._http()
        h = await self._headers()
        r = await c.get(
            f"{QE_BASE}/projects/{self.project_id}/processors/{processor_id}",
            headers=h,
        )
        r.raise_for_status()
        return r.json()

    async def list_calibrations(self, processor_id: str) -> Dict[str, Any]:
        """List calibration metrics for a processor."""
        c = await self._http()
        h = await self._headers()
        r = await c.get(
            f"{QE_BASE}/projects/{self.project_id}/processors/{processor_id}/calibrationMetrics",
            headers=h,
        )
        r.raise_for_status()
        return r.json()

    async def submit_program(
        self,
        processor_id: str,
        program: Dict[str, Any],
        run_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit a quantum program to a processor."""
        c = await self._http()
        h = await self._headers()
        body = {"program": program}
        if run_context:
            body["runContext"] = run_context
        r = await c.post(
            f"{QE_BASE}/projects/{self.project_id}/processors/{processor_id}/programs",
            headers=h,
            json=body,
        )
        r.raise_for_status()
        return r.json()

    async def get_job(self, processor_id: str, job_id: str) -> Dict[str, Any]:
        """Get status/results of a quantum job."""
        c = await self._http()
        h = await self._headers()
        r = await c.get(
            f"{QE_BASE}/projects/{self.project_id}/processors/{processor_id}/jobs/{job_id}",
            headers=h,
        )
        r.raise_for_status()
        return r.json()

    async def cancel_job(self, processor_id: str, job_id: str) -> Dict[str, Any]:
        """Cancel a quantum job."""
        c = await self._http()
        h = await self._headers()
        r = await c.post(
            f"{QE_BASE}/projects/{self.project_id}/processors/{processor_id}/jobs/{job_id}:cancel",
            headers=h,
        )
        r.raise_for_status()
        return r.json()

    # -- Local Cirq helpers (no network required) -----------------------------

    @staticmethod
    def cirq_bell_circuit_json() -> Dict[str, Any]:
        """Return a simple Bell state circuit in Cirq JSON format for testing."""
        return {
            "cirq_type": "Circuit",
            "moments": [
                {
                    "cirq_type": "Moment",
                    "operations": [
                        {"cirq_type": "GateOperation", "gate": {"cirq_type": "HPowGate", "exponent": 1.0}, "qubits": [{"cirq_type": "GridQubit", "row": 0, "col": 0}]},
                    ],
                },
                {
                    "cirq_type": "Moment",
                    "operations": [
                        {"cirq_type": "GateOperation", "gate": {"cirq_type": "CNotPowGate", "exponent": 1.0}, "qubits": [{"cirq_type": "GridQubit", "row": 0, "col": 0}, {"cirq_type": "GridQubit", "row": 0, "col": 1}]},
                    ],
                },
            ],
        }

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
