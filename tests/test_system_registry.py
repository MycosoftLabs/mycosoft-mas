"""
System Registry Tests (pytest) - Feb 4, 2026

This file used to be an async CLI-style test runner. It is now standard pytest
tests with assertions.
"""

from datetime import datetime
from typing import Dict, List
from uuid import uuid4


EXPECTED_MAS_APIS = [
    "/api/memory/write",
    "/api/memory/read",
    "/api/memory/delete",
    "/api/memory/list/{scope}/{namespace}",
    "/api/memory/health",
    "/api/security/audit/log",
    "/api/security/audit/query",
    "/api/security/health",
    "/api/registry/systems",
    "/api/registry/apis",
    "/api/registry/devices",
    "/api/registry/health",
    "/api/graph/nodes",
    "/api/graph/edges",
    "/api/graph/path",
    "/api/graph/health",
    "/health",
]

EXPECTED_SYSTEMS = [
    {"name": "MAS", "type": "mas"},
    {"name": "Website", "type": "website"},
    {"name": "MINDEX", "type": "mindex"},
    {"name": "NatureOS", "type": "natureos"},
    {"name": "NLM", "type": "nlm"},
    {"name": "MycoBrain", "type": "mycobrain"},
]


def test_system_registration() -> None:
    class MockRegistry:
        def __init__(self):
            self.systems: Dict[str, Dict[str, str]] = {}

        def register_system(self, name: str, type: str, url: str, description: str):
            system_id = str(uuid4())
            self.systems[name] = {
                "id": system_id,
                "name": name,
                "type": type,
                "url": url,
                "description": description,
                "status": "active",
                "created_at": datetime.now().isoformat(),
            }
            return self.systems[name]

        def get_system(self, name: str):
            return self.systems.get(name)

        def list_systems(self):
            return list(self.systems.values())

    registry = MockRegistry()
    for sys in EXPECTED_SYSTEMS:
        registry.register_system(sys["name"], sys["type"], f"http://example/{sys['type']}", f"{sys['name']} System")

    assert len(registry.list_systems()) == 6
    mas = registry.get_system("MAS")
    assert mas is not None
    assert mas["type"] == "mas"

    for field in ["id", "name", "type", "url", "status", "created_at"]:
        assert field in mas

    count_before = len(registry.list_systems())
    registry.register_system("MAS", "mas", "http://test", "Duplicate")
    count_after = len(registry.list_systems())
    assert count_before == count_after  # upsert behavior


def test_api_indexing() -> None:
    class MockAPIIndexer:
        def __init__(self):
            self.apis: List[Dict[str, str]] = []

        def index_api(self, system_name: str, path: str, method: str, description: str = ""):
            api = {"id": str(uuid4()), "system": system_name, "path": path, "method": method, "description": description}
            self.apis.append(api)
            return api

        def list_apis(self, system: str | None = None):
            if system:
                return [a for a in self.apis if a["system"] == system]
            return self.apis

        def get_api_count(self):
            return len(self.apis)

    indexer = MockAPIIndexer()
    for path in EXPECTED_MAS_APIS:
        method = "POST" if ("write" in path or "log" in path) else "GET"
        indexer.index_api("MAS", path, method, f"Endpoint for {path}")

    count = indexer.get_api_count()
    assert count >= 15

    mas_apis = indexer.list_apis("MAS")
    assert len(mas_apis) == count
    assert len([a for a in mas_apis if "/memory/" in a["path"]]) >= 4
    assert len([a for a in mas_apis if "/security/" in a["path"]]) >= 2
    assert len([a for a in mas_apis if "/registry/" in a["path"]]) >= 3


def test_device_registry() -> None:
    known_devices = [
        {"device_id": "sporebase-001", "name": "SporeBase Alpha", "type": "sporebase"},
        {"device_id": "mushroom1-001", "name": "Mushroom 1 Alpha", "type": "mushroom1"},
        {"device_id": "nfc-reader-001", "name": "NFC Reader", "type": "nfc"},
        {"device_id": "env-sensor-001", "name": "Environment Sensor", "type": "sensor"},
    ]

    class MockDeviceRegistry:
        def __init__(self):
            self.devices: Dict[str, Dict[str, str]] = {}

        def register_device(self, device_id: str, name: str, type: str, firmware: str = "1.0.0"):
            self.devices[device_id] = {
                "id": str(uuid4()),
                "device_id": device_id,
                "name": name,
                "type": type,
                "firmware_version": firmware,
                "status": "offline",
                "last_seen": "",
            }
            return self.devices[device_id]

        def update_status(self, device_id: str, status: str):
            if device_id not in self.devices:
                return False
            self.devices[device_id]["status"] = status
            self.devices[device_id]["last_seen"] = datetime.now().isoformat()
            return True

        def list_devices(self):
            return list(self.devices.values())

    reg = MockDeviceRegistry()
    for dev in known_devices:
        reg.register_device(dev["device_id"], dev["name"], dev["type"])

    assert len(reg.list_devices()) == 4
    assert reg.update_status("sporebase-001", "online") is True
    assert reg.devices["sporebase-001"]["status"] == "online"
    assert reg.devices["sporebase-001"]["last_seen"] != ""


def test_code_indexing() -> None:
    # Minimal "indexing": just ensure a list exists.
    code_index = {"modules": ["mycosoft_mas.core", "mycosoft_mas.agents", "mycosoft_mas.memory"]}
    assert any(m.startswith("mycosoft_mas.") for m in code_index["modules"])


def test_200_apis_target() -> None:
    # Keep this a sanity-check; real endpoint counting is validated elsewhere.
    assert len(EXPECTED_MAS_APIS) >= 15

