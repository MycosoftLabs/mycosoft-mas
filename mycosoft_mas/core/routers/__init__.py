"""Router package exports.

Routers are loaded lazily so importing one lightweight router does not pull in
every optional ML/science dependency.
"""

from __future__ import annotations

from importlib import import_module

_ROUTERS = {
    "agents": ".agents",
    "tasks": ".tasks",
    "dashboard": ".dashboard",
    "integrations": ".integrations",
    "search_memory": ".search_memory_api",
    "earth2_memory": ".earth2_memory_api",
    "voice_command": ".voice_command_api",
    "timeline": ".timeline_api",
    "prediction": ".prediction_api",
    "knowledge_graph": ".knowledge_graph_api",
    "physicsnemo": ".physicsnemo_api",
    "fci": ".fci_api",
    "fci_websocket": ".fci_websocket",
    "provenance": ".provenance_api",
    "governance": ".governance_api",
}

__all__ = sorted(_ROUTERS)


def __getattr__(name: str):
    if name not in _ROUTERS:
        raise AttributeError(name)
    module = import_module(_ROUTERS[name], __name__)
    router = getattr(module, "router")
    globals()[name] = router
    return router
