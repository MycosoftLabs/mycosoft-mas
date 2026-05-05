"""
Layer 2 — scheduled scoped checks against Sandbox (187) only.

Records redteam_runs + findings in Postgres. Uses `nmap` when available on the
MAS host (Linux); otherwise records a skipped finding (no fake scan output).
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import shutil
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _pg() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def run_layer2_once() -> Dict[str, Any]:
    if not _pg():
        return {"skipped": True}
    from mycosoft_mas.soc import repository as soc_repo

    scope = os.getenv("SOC_REDTEAM_L2_TARGET", "192.168.0.187")
    run_id = await soc_repo.create_redteam_run(
        layer=2,
        scope="sandbox_scoped",
        tool="nmap_sn",
        params={"target": scope, "host": platform.node()},
    )
    nmap = shutil.which("nmap")
    if not nmap or platform.system() == "Windows":
        await soc_repo.insert_redteam_finding(
            run_id=run_id,
            severity="info",
            control_id="3.14.2",
            title="nmap not available on this runtime — L2 scan skipped",
            evidence={"reason": "nmap missing or Windows host", "scope": scope},
        )
        await soc_repo.finish_redteam_run(
            run_id,
            "completed",
            "Layer 2 skipped (toolchain)",
            "nmap not installed or unsupported OS",
        )
        return {"run_id": str(run_id), "skipped": True}

    proc = await asyncio.create_subprocess_exec(
        nmap,
        "-sn",
        "-T4",
        scope,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out_b, err_b = await proc.communicate()
    out = (out_b or b"").decode(errors="ignore")[:8000]
    err = (err_b or b"").decode(errors="ignore")[:2000]
    ok = proc.returncode == 0
    await soc_repo.insert_redteam_finding(
        run_id=run_id,
        severity="info" if ok else "medium",
        control_id="3.14.2",
        title=f"nmap -sn {scope}",
        evidence={"returncode": proc.returncode, "stdout_tail": out[-4000:], "stderr_tail": err},
    )
    await soc_repo.finish_redteam_run(
        run_id,
        "completed" if ok else "failed",
        "nmap host discovery",
        out[:12000],
    )
    return {"run_id": str(run_id), "returncode": proc.returncode}


async def _loop() -> None:
    interval = int(os.getenv("SOC_REDTEAM_L2_INTERVAL_SEC", "86400"))
    logger.info("Red team L2 loop starting (interval=%ss)", interval)
    while True:
        try:
            await run_layer2_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("layer2 failed: %s", e)
        await asyncio.sleep(max(3600, interval))


_task: Optional[asyncio.Task[None]] = None


def start_redteam_layer2_background() -> None:
    global _task
    if os.getenv("SOC_REDTEAM_L2", "1") == "0":
        return
    if not _pg():
        return
    if _task and not _task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_loop(), name="redteam-layer2")
