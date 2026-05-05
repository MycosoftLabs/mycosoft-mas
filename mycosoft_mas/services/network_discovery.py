"""
LAN discovery: UniFi clients/devices, HTTP service fingerprint, optional ip neigh, MQTT status URL.
Writes reconciled rows into soc_ops.device_inventory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROBE_MATRIX: List[tuple[str, int, str]] = [
    ("192.168.0.123", 8787, "jetson_gateway"),
    ("192.168.0.228", 8787, "jetson_gateway"),
    ("192.168.0.187", 3000, "website_sandbox"),
    ("192.168.0.188", 8001, "mas_orchestrator"),
    ("192.168.0.189", 8000, "mindex_api"),
    ("192.168.0.191", 443, "myca_workspace_https"),
    ("192.168.0.241", 8999, "voice_bridge"),
    ("192.168.0.249", 8220, "earth2_api"),
]


def _pg() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def _probe_http(host: str, port: int, role: str) -> None:
    if not _pg():
        return
    import httpx

    from mycosoft_mas.soc import repository as soc_repo

    url = f"http://{host}:{port}/"
    status = "offline"
    raw: Dict[str, Any] = {"url": url, "role_hint": role}
    try:
        async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
            r = await client.get(url)
            raw["http_status"] = r.status_code
            status = "online" if r.status_code < 500 else "degraded"
    except Exception as e:
        raw["error"] = str(e)[:200]

    await soc_repo.upsert_device_inventory(
        mac=None,
        ip=host,
        hostname=role.replace("_", " "),
        board_type=role,
        device_id=f"probe-{host}-{port}",
        source="http_probe",
        classified_as=role,
        status=status,
        capabilities={"ports": [port]},
        raw=raw,
    )


async def _ingest_unifi() -> int:
    if not _pg():
        return 0
    from mycosoft_mas.integrations.unifi_client import UniFiClient
    from mycosoft_mas.soc import repository as soc_repo

    client = UniFiClient()
    if not client.is_configured():
        return 0
    n = 0
    for sta in await client.get_clients():
        mac = (sta.get("mac") or "").lower()
        ip = sta.get("ip") or sta.get("last_ip")
        if not ip and not mac:
            continue
        hostname = sta.get("hostname") or sta.get("name") or sta.get("oui", "")
        await soc_repo.upsert_device_inventory(
            mac=mac or None,
            ip=str(ip) if ip else None,
            hostname=str(hostname) if hostname else None,
            board_type=sta.get("dev_cat") or sta.get("type"),
            device_id=sta.get("_id") or mac or str(ip),
            source="unifi",
            classified_as=sta.get("dev_cat") or "client",
            status="online" if sta.get("connected", True) else "offline",
            capabilities={"unifi": {k: sta.get(k) for k in ("channel", "radio", "essid") if sta.get(k)}},
            raw=sta,
        )
        n += 1
    for dev in await client.get_devices():
        mac = (dev.get("mac") or "").lower()
        ip = dev.get("ip")
        if not mac and not ip:
            continue
        await soc_repo.upsert_device_inventory(
            mac=mac or None,
            ip=str(ip) if ip else None,
            hostname=dev.get("name") or dev.get("model"),
            board_type=dev.get("model"),
            device_id=dev.get("_id") or mac or str(ip),
            source="unifi",
            classified_as=dev.get("type") or "infra",
            status="online" if dev.get("state") == 1 else "offline",
            capabilities={},
            raw=dev,
        )
        n += 1
    return n


async def _ingest_ip_neigh() -> int:
    if not _pg():
        return 0
    from mycosoft_mas.soc import repository as soc_repo

    try:
        proc = await asyncio.create_subprocess_exec(
            "ip",
            "-4",
            "neigh",
            "show",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            return 0
    except Exception:
        return 0

    text = out.decode(errors="ignore")
    n = 0
    for line in text.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+lladdr\s+([0-9a-f:]+)", line, re.I)
        if not m:
            continue
        ip, mac = m.group(1), m.group(2).lower()
        await soc_repo.upsert_device_inventory(
            mac=mac,
            ip=ip,
            hostname=None,
            board_type=None,
            device_id=f"arp-{mac}",
            source="arp",
            classified_as="lan_host",
            status="stale",
            capabilities={},
            raw={"line": line.strip()},
        )
        n += 1
    return n


async def _ingest_mqtt_status() -> int:
    if not _pg():
        return 0
    import httpx

    from mycosoft_mas.soc import repository as soc_repo

    url = os.getenv("MQTT_STATUS_URL", "https://mqtt-status.mycosoft.com/")
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=True) as client:
            r = await client.get(url)
            if not r.is_success:
                return 0
            data = r.json()
    except Exception as e:
        logger.debug("mqtt status fetch failed: %s", e)
        return 0

    await soc_repo.upsert_device_inventory(
        mac=None,
        ip=None,
        hostname="mqtt_status_endpoint",
        board_type="mqtt",
        device_id="mqtt-status-feed",
        source="mqtt",
        classified_as="broker_status",
        status="online",
        capabilities={"keys": list(data.keys())[:20]} if isinstance(data, dict) else {},
        raw=data if isinstance(data, dict) else {"body": str(data)[:4000]},
    )
    return 1


async def _jetson_ssh_mycobrain_probe(host: str) -> None:
    """
    Optional: SSH to Jetson and read local MycoBrain HTTP health (MAS VM only).
    Enable with JETSON_SSH_ONBOARD=1 and JETSON_SSH_PASSWORD or VM_PASSWORD.
    """
    if os.getenv("JETSON_SSH_ONBOARD", "0") != "1":
        return
    if not _pg():
        return
    pwd = os.getenv("JETSON_SSH_PASSWORD") or os.getenv("VM_PASSWORD") or ""
    user = os.getenv("JETSON_SSH_USER", "jetson")
    if not pwd:
        logger.info("JETSON_SSH_ONBOARD=1 but no JETSON_SSH_PASSWORD/VM_PASSWORD; skip %s", host)
        return

    def _ssh() -> Dict[str, Any]:
        try:
            import paramiko  # type: ignore

            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(host, username=user, password=pwd, timeout=14, banner_timeout=14)
            _, stdout, stderr = c.exec_command(
                "curl -s -S --max-time 5 http://127.0.0.1:8003/health 2>/dev/null || true", timeout=18
            )
            out = stdout.read().decode(errors="ignore")[:800]
            err = stderr.read().decode(errors="ignore")[:400]
            c.close()
            return {"ok": True, "stdout": out, "stderr": err}
        except Exception as e:
            return {"ok": False, "error": str(e)[:400]}

    raw = await asyncio.to_thread(_ssh)
    from mycosoft_mas.soc import repository as soc_repo

    await soc_repo.upsert_device_inventory(
        mac=None,
        ip=host,
        hostname=f"jetson_ssh_{user}",
        board_type="jetson_mycobrain_probe",
        device_id=f"jetson-ssh-{host}",
        source="ssh_probe",
        classified_as="jetson",
        status="online" if raw.get("ok") and raw.get("stdout") else "degraded",
        capabilities={"ssh_user": user, "mycobrain_health_snippet": (raw.get("stdout") or "")[:200]},
        raw=raw,
    )


async def run_discovery_cycle() -> Dict[str, Any]:
    if not _pg():
        return {"skipped": True, "reason": "no_database"}
    counts = {"unifi": 0, "arp": 0, "mqtt": 0, "http": 0, "jetson_ssh": 0}
    try:
        counts["unifi"] = await _ingest_unifi()
    except Exception as e:
        logger.warning("UniFi ingest: %s", e)
    try:
        counts["arp"] = await _ingest_ip_neigh()
    except Exception as e:
        logger.debug("ARP neigh: %s", e)
    try:
        counts["mqtt"] = await _ingest_mqtt_status()
    except Exception as e:
        logger.debug("MQTT status: %s", e)
    for host, port, role in PROBE_MATRIX:
        try:
            await _probe_http(host, port, role)
            counts["http"] += 1
        except Exception as e:
            logger.debug("probe %s:%s %s", host, port, e)
    for jet_ip in ("192.168.0.123", "192.168.0.228"):
        try:
            await _jetson_ssh_mycobrain_probe(jet_ip)
            counts["jetson_ssh"] += 1
        except Exception as e:
            logger.debug("jetson ssh %s: %s", jet_ip, e)
    return counts


async def _network_discovery_loop() -> None:
    interval = int(os.getenv("SOC_NETWORK_DISCOVERY_INTERVAL_SEC", "300"))
    logger.info("Network discovery loop starting (interval=%ss)", interval)
    while True:
        try:
            summary = await run_discovery_cycle()
            logger.info("network_discovery cycle: %s", json.dumps(summary, default=str))
            try:
                from mycosoft_mas.core.routers.security_stream import broadcast_security_event

                await broadcast_security_event(
                    "device_inventory",
                    "LAN inventory updated",
                    json.dumps(summary, default=str)[:500],
                    "info",
                    {"counts": summary},
                )
            except Exception as be:
                logger.debug("broadcast device_inventory: %s", be)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("network_discovery cycle failed: %s", e)
        await asyncio.sleep(max(60, interval))


_task: Optional[asyncio.Task[None]] = None


def start_network_discovery_background() -> None:
    """Schedule the discovery loop (idempotent)."""
    global _task
    if os.getenv("SOC_NETWORK_DISCOVERY", "1") == "0":
        logger.info("SOC_NETWORK_DISCOVERY=0; skipping network discovery background")
        return
    if not _pg():
        return
    if _task and not _task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_network_discovery_loop(), name="network-discovery")
