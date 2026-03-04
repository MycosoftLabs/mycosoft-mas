"""
Tecan Lab Automation Integration Client.

Worklist generation (GWL/CSV), plate layout, liquid handling protocols.
Tecan FluentControl uses SiLA2 protocol; this client focuses on file-based
GWL worklist generation for programmatic liquid handling.

Environment Variables:
    TECAN_FLUENT_URL: Optional FluentControl/SiLA2 endpoint (e.g. http://localhost:50053)
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class TecanClient:
    """Client for Tecan lab automation - GWL worklist generation and optional API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.fluent_url = self.config.get("fluent_url", os.getenv("TECAN_FLUENT_URL", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def create_aspirate(
        self,
        rack_label: str,
        rack_id: str,
        rack_type: str,
        position: int,
        volume: float,
        liquid_class: str = "Water",
        tip_type: str = "Standard",
        tube_id: str = "",
        tip_mask: str = "0",
        forced_rack_type: str = "",
    ) -> str:
        """Create a GWL aspirate command line."""
        return (
            f"A;{rack_label};{rack_id};{rack_type};{position};{tube_id};"
            f"{volume};{liquid_class};{tip_type};{tip_mask};{forced_rack_type}"
        )

    def create_dispense(
        self,
        rack_label: str,
        rack_id: str,
        rack_type: str,
        position: int,
        volume: float,
        liquid_class: str = "Water",
        tip_type: str = "Standard",
        tube_id: str = "",
        tip_mask: str = "0",
        forced_rack_type: str = "",
    ) -> str:
        """Create a GWL dispense command line."""
        return (
            f"D;{rack_label};{rack_id};{rack_type};{position};{tube_id};"
            f"{volume};{liquid_class};{tip_type};{tip_mask};{forced_rack_type}"
        )

    def create_wash_tips(self) -> str:
        """Create a GWL wash/drop tips command."""
        return "W;"

    def generate_transfer_worklist(
        self,
        source: Tuple[str, str, str, int],
        dest: Tuple[str, str, str, int],
        volume: float,
        liquid_class: str = "Water",
        drop_tip_after: bool = True,
    ) -> List[str]:
        """Generate aspirate-dispense transfer. source/dest: (rack_label, rack_id, rack_type, position)."""
        lines = [
            self.create_aspirate(source[0], source[1], source[2], source[3], volume, liquid_class),
            self.create_dispense(dest[0], dest[1], dest[2], dest[3], volume, liquid_class),
        ]
        if drop_tip_after:
            lines.append(self.create_wash_tips())
        return lines

    def generate_serial_dilution(
        self,
        source_rack: str,
        source_id: str,
        source_type: str,
        dest_rack: str,
        dest_id: str,
        dest_type: str,
        source_positions: List[int],
        dest_positions: List[int],
        transfer_volume: float,
        liquid_class: str = "Water",
    ) -> str:
        """Generate GWL content for serial dilution (multi-well transfer)."""
        lines = []
        for sp, dp in zip(source_positions, dest_positions):
            lines.extend(
                self.generate_transfer_worklist(
                    (source_rack, source_id, source_type, sp),
                    (dest_rack, dest_id, dest_type, dp),
                    transfer_volume,
                    liquid_class,
                    drop_tip_after=True,
                )
            )
        return "\n".join(lines)

    def write_gwl(self, lines: List[str], path: str) -> None:
        """Write GWL worklist to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(lines) + "\n"
        Path(path).write_text(content, encoding="utf-8")

    def gwl_to_string(self, lines: List[str]) -> str:
        """Return GWL content as string."""
        return "\n".join(lines) + "\n"

    async def submit_worklist(self, gwl_content: str) -> Dict[str, Any]:
        """Submit worklist to FluentControl (if TECAN_FLUENT_URL set). Placeholder for SiLA2."""
        if not self.fluent_url:
            return {"ok": False, "message": "TECAN_FLUENT_URL not configured"}
        client = await self._get_client()
        try:
            r = await client.post(
                f"{self.fluent_url.rstrip('/')}/worklist",
                content=gwl_content,
                headers={"Content-Type": "text/plain"},
            )
            r.raise_for_status()
            return {"ok": True, "message": "Worklist submitted"}
        except Exception as e:
            logger.warning("Tecan worklist submit failed: %s", e)
            return {"ok": False, "message": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check connectivity to FluentControl (if configured)."""
        if not self.fluent_url:
            return {"ok": True, "message": "File-based mode (no Fluent URL)"}
        try:
            client = await self._get_client()
            r = await client.get(f"{self.fluent_url.rstrip('/')}/health")
            return {"ok": r.status_code == 200, "message": "Fluent reachable" if r.ok else "Fluent error"}
        except Exception as e:
            return {"ok": False, "message": str(e)}
