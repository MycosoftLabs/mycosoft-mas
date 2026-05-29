"""
Firmware compatibility audit for MycoBrain field and serial devices.

Compares registry + agent probe data against the canonical Side A MDP build matrix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

CANONICAL_SIDE_A_VERSION = "side-a-mdp-2.1.0"
CANONICAL_SIDE_B_VERSION = "side-b-mdp-2.1.0"

COMPATIBILITY_MATRIX: List[Dict[str, Any]] = [
    {
        "capability": "mdp_v1_commands",
        "label": "MDP v1 commands",
        "required_for": "Console, Earth Simulator widgets",
        "min_firmware": "side-a-mdp-2.0.0",
    },
    {
        "capability": "buzzer_presets",
        "label": "Buzzer presets",
        "required_for": "BuzzerControlWidget",
        "min_firmware": "side-a-mdp-2.0.0",
        "requires_modules": ["buzzer"],
    },
    {
        "capability": "neopixel_patterns",
        "label": "NeoPixel patterns",
        "required_for": "LedControlWidget rainbow/off",
        "min_firmware": "side-a-mdp-2.0.0",
        "requires_modules": ["neopixel"],
    },
    {
        "capability": "i2c_peripheral_grid",
        "label": "I2C peripheral grid",
        "required_for": "PeripheralGrid scan/status",
        "min_firmware": "side-a-mdp-2.0.0",
        "requires_modules": ["i2c"],
    },
    {
        "capability": "optical_acoustic_tx",
        "label": "Optical/acoustic TX",
        "required_for": "CommunicationPanel TX tabs",
        "min_firmware": "side-a-mdp-2.1.0",
        "note": "Not fully present in SideA_MDP 2.1.0 — ScienceComms port pending",
    },
    {
        "capability": "openclaw_agent",
        "label": "OpenClaw / NemoClaw agent",
        "required_for": "MAS relay firmware tasks",
        "min_firmware": None,
        "requires_edge": "openclaw_18789",
    },
]

_TIER_ORDER = {"compatible": 0, "partial": 1, "incompatible": 2, "unknown": 3}


@dataclass
class FirmwareAuditEntry:
    device_id: str
    device_name: str = ""
    device_role: str = ""
    board_type: str = ""
    firmware_version: str = ""
    mdp_version: Optional[int] = None
    capabilities: List[str] = field(default_factory=list)
    agent_url: Optional[str] = None
    agent_probe: Dict[str, Any] = field(default_factory=dict)
    openclaw_probe: Dict[str, Any] = field(default_factory=dict)
    compatibility_tier: str = "unknown"
    missing_capabilities: List[str] = field(default_factory=list)
    recommended_action: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_role": self.device_role,
            "board_type": self.board_type,
            "firmware_version": self.firmware_version,
            "mdp_version": self.mdp_version,
            "capabilities": self.capabilities,
            "agent_url": self.agent_url,
            "agent_probe": self.agent_probe,
            "openclaw_probe": self.openclaw_probe,
            "compatibility_tier": self.compatibility_tier,
            "missing_capabilities": self.missing_capabilities,
            "recommended_action": self.recommended_action,
            "errors": self.errors,
        }


def _parse_semver_tuple(version: str) -> Tuple[int, ...]:
    if not version:
        return ()
    cleaned = version.strip().lower()
    cleaned = cleaned.replace("side-a-mdp-", "").replace("side-b-mdp-", "")
    cleaned = cleaned.replace("v", "")
    parts: List[int] = []
    for chunk in re.split(r"[.\-_]", cleaned):
        if chunk.isdigit():
            parts.append(int(chunk))
    return tuple(parts)


def _version_gte(current: str, minimum: str) -> bool:
    cur = _parse_semver_tuple(current)
    min_v = _parse_semver_tuple(minimum)
    if not cur or not min_v:
        return False
    length = max(len(cur), len(min_v))
    cur_padded = cur + (0,) * (length - len(cur))
    min_padded = min_v + (0,) * (length - len(min_v))
    return cur_padded >= min_padded


def _resolve_agent_url(device: Dict[str, Any]) -> Optional[str]:
    extra = device.get("extra") or {}
    agent_url = extra.get("agent_url")
    if isinstance(agent_url, str) and agent_url.strip():
        return agent_url.rstrip("/")
    host = device.get("host") or ""
    port = int(device.get("port") or 8003)
    if not host:
        return None
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}:{port}"


def _resolve_openclaw_url(device: Dict[str, Any], agent_url: Optional[str]) -> Optional[str]:
    extra = device.get("extra") or {}
    oc = extra.get("openclaw_url")
    if isinstance(oc, str) and oc.strip():
        return oc.rstrip("/")
    if agent_url and ":8787" in agent_url:
        return agent_url.replace(":8787", ":18789")
    host = device.get("host") or ""
    if host and not host.startswith("http"):
        return f"http://{host}:18789"
    return None


async def _probe_url(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    try:
        r = await client.get(url)
        if r.status_code >= 400:
            return {"reachable": False, "status_code": r.status_code}
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return {"reachable": True, "status_code": r.status_code, "body": body}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


async def probe_agent(agent_url: str, timeout: float = 5.0) -> Dict[str, Any]:
    base = agent_url.rstrip("/")
    async with httpx.AsyncClient(timeout=timeout) as client:
        paths = ("/api/status", "/status", "/info", "/health", "/devices")
        for path in paths:
            probe = await _probe_url(client, f"{base}{path}")
            if probe.get("reachable"):
                probe["path"] = path
                body = probe.get("body") or {}
                if isinstance(body, dict):
                    probe["fw_version"] = (
                        body.get("fw_version")
                        or body.get("firmware_version")
                        or (body.get("side_a") or {}).get("firmware_version")
                        or (body.get("record") or {}).get("firmware_version")
                        or (body.get("lastSensorReading") or {}).get("fw_version")
                    )
                    if not probe.get("fw_version"):
                        for dev in body.get("devices") or []:
                            if isinstance(dev, dict) and dev.get("firmware_version"):
                                probe["fw_version"] = dev["firmware_version"]
                                break
                    probe["serial_connected"] = body.get(
                        "serialConnected", body.get("serial_connected")
                    )
                    probe["openclaw"] = body.get("openclaw")
                return probe
        return {"reachable": False, "error": "no_status_endpoint"}


async def probe_openclaw(openclaw_url: str, timeout: float = 5.0) -> Dict[str, Any]:
    base = openclaw_url.rstrip("/")
    async with httpx.AsyncClient(timeout=timeout) as client:
        for path in ("/health", "/healthz", "/readyz"):
            probe = await _probe_url(client, f"{base}{path}")
            if probe.get("reachable"):
                probe["path"] = path
                return probe
        return {"reachable": False, "error": "openclaw_unreachable"}


def score_firmware(
    firmware_version: str,
    capabilities: List[str],
    agent_probe: Dict[str, Any],
    openclaw_probe: Dict[str, Any],
) -> Tuple[str, List[str], str]:
    fw = (firmware_version or "").strip() or str(agent_probe.get("fw_version") or "")
    caps = {c.lower() for c in capabilities}
    missing: List[str] = []

    for row in COMPATIBILITY_MATRIX:
        cap_id = row["capability"]
        min_fw = row.get("min_firmware")
        if min_fw and fw and not _version_gte(fw, min_fw):
            missing.append(cap_id)
            continue
        if min_fw and not fw:
            missing.append(cap_id)
            continue
        for mod in row.get("requires_modules") or []:
            if mod.lower() not in caps and fw and not _version_gte(fw, min_fw or CANONICAL_SIDE_A_VERSION):
                missing.append(cap_id)
                break
        if cap_id == "openclaw_agent":
            if not openclaw_probe.get("reachable"):
                missing.append(cap_id)

    if not fw:
        return "unknown", missing, "Probe agent or connect USB to read firmware_version"

    if fw == CANONICAL_SIDE_A_VERSION and not missing:
        return "compatible", missing, "On canonical Side A MDP 2.1.0"

    if fw and _version_gte(fw, "side-a-mdp-2.0.0") and len(missing) <= 2:
        return "partial", missing, f"Upgrade to {CANONICAL_SIDE_A_VERSION} for full widget parity"

    if fw:
        return "incompatible", missing, f"Flash MycoBrain_SideA_MDP env mushroom1/hyphae1 → {CANONICAL_SIDE_A_VERSION}"

    return "unknown", missing, "Firmware version not reported"


async def audit_device(device_id: str, device: Dict[str, Any]) -> FirmwareAuditEntry:
    extra = device.get("extra") or {}
    fw = str(device.get("firmware_version") or extra.get("firmware_version") or "")
    caps_raw = device.get("capabilities") or extra.get("capabilities") or []
    if isinstance(caps_raw, dict):
        caps = list(caps_raw.keys())
    elif isinstance(caps_raw, list):
        caps = [str(c) for c in caps_raw]
    else:
        caps = []

    entry = FirmwareAuditEntry(
        device_id=device_id,
        device_name=str(device.get("device_name") or device.get("name") or device_id),
        device_role=str(device.get("device_role") or ""),
        board_type=str(device.get("board_type") or ""),
        firmware_version=fw,
        mdp_version=extra.get("mdp_version"),
        capabilities=caps,
    )

    agent_url = _resolve_agent_url(device)
    entry.agent_url = agent_url

    if agent_url:
        try:
            entry.agent_probe = await probe_agent(agent_url)
            probed_fw = entry.agent_probe.get("fw_version")
            if probed_fw and not entry.firmware_version:
                entry.firmware_version = str(probed_fw)
        except Exception as exc:
            entry.errors.append(f"agent_probe: {exc}")

    oc_url = _resolve_openclaw_url(device, agent_url)
    if oc_url:
        try:
            entry.openclaw_probe = await probe_openclaw(oc_url)
        except Exception as exc:
            entry.errors.append(f"openclaw_probe: {exc}")

    tier, missing, action = score_firmware(
        entry.firmware_version, entry.capabilities, entry.agent_probe, entry.openclaw_probe
    )
    entry.compatibility_tier = tier
    entry.missing_capabilities = missing
    entry.recommended_action = action
    return entry


async def audit_registry(devices: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    entries: List[FirmwareAuditEntry] = []
    for device_id, device in devices.items():
        entries.append(await audit_device(device_id, device))

    entries.sort(key=lambda e: (_TIER_ORDER.get(e.compatibility_tier, 9), e.device_id))

    summary = {
        "compatible": sum(1 for e in entries if e.compatibility_tier == "compatible"),
        "partial": sum(1 for e in entries if e.compatibility_tier == "partial"),
        "incompatible": sum(1 for e in entries if e.compatibility_tier == "incompatible"),
        "unknown": sum(1 for e in entries if e.compatibility_tier == "unknown"),
        "total": len(entries),
    }

    return {
        "canonical_side_a": CANONICAL_SIDE_A_VERSION,
        "canonical_side_b": CANONICAL_SIDE_B_VERSION,
        "compatibility_matrix": COMPATIBILITY_MATRIX,
        "summary": summary,
        "devices": [e.to_dict() for e in entries],
    }
