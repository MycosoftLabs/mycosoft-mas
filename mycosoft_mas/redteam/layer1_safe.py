"""
Layer 1 — continuous SAFE checks on production (MAS host).
TLS reachability + allowlisted public endpoints; records redteam_runs + findings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import ssl
import socket
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SAFE_TARGETS: List[str] = [
    "mycosoft.com:443",
    "sandbox.mycosoft.com:443",
    "192.168.0.188:8001",
    "192.168.0.189:8000",
]


def _pg() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def _http_health(host: str, port: int, tls: bool) -> Dict[str, Any]:
    import httpx

    scheme = "https" if tls else "http"
    url = f"{scheme}://{host}:{port}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            r = await client.get(url)
            return {"ok": r.status_code < 500, "http_status": r.status_code, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)[:500], "url": url}


async def _tls_socket_check(host: str, port: int) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()

    def _sync() -> Dict[str, Any]:
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    return {
                        "ok": True,
                        "subject": dict(x[0] for x in cert.get("subject", [])) if cert else {},
                    }
        except Exception as e:
            return {"ok": False, "error": str(e)[:500]}

    return await loop.run_in_executor(None, _sync)


async def _endpoint_check(host: str, port: int) -> Dict[str, Any]:
    if port in (443, 8443):
        return await _tls_socket_check(host, port)
    return await _http_health(host, port, tls=False)


async def run_layer1_once() -> Dict[str, Any]:
    if not _pg():
        return {"skipped": True}
    from mycosoft_mas.soc import repository as soc_repo

    run_id = await soc_repo.create_redteam_run(
        layer=1,
        scope="prod_safe_tls",
        tool="socket_tls",
        params={"targets": SAFE_TARGETS},
    )
    findings = 0
    for t in SAFE_TARGETS:
        host, _, port_s = t.partition(":")
        port = int(port_s or "443")
        res = await _endpoint_check(host, port)
        sev = "info" if res.get("ok") else "medium"
        await soc_repo.insert_redteam_finding(
            run_id=run_id,
            severity=sev,
            title=f"TLS check {t}",
            evidence=res,
            control_id="3.13.1",
        )
        findings += 1
    await soc_repo.finish_redteam_run(run_id, "completed", f"{findings} checks")
    return {"run_id": str(run_id), "findings": findings}


async def _layer1_loop() -> None:
    interval = int(os.getenv("SOC_REDTEAM_L1_INTERVAL_SEC", "900"))
    logger.info("Red team L1 loop starting (interval=%ss)", interval)
    while True:
        try:
            await run_layer1_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("layer1 run failed: %s", e)
        await asyncio.sleep(max(120, interval))


_task: Optional[asyncio.Task[None]] = None


def start_redteam_layer1_background() -> None:
    global _task
    if os.getenv("SOC_REDTEAM_L1", "1") == "0":
        return
    if not _pg():
        return
    if _task and not _task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_layer1_loop(), name="redteam-layer1")
