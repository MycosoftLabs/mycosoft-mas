"""
Capability Foundry — Safe skill acquisition pipeline.

When MYCA is asked for something she can't do yet, this module handles:
1. Detect the missing capability
2. Search approved sources for code, packages, APIs, MCP servers
3. Build an adapter or tool wrapper
4. Spin it up in a sandbox
5. Write and run tests
6. Run policy checks, security checks, and evals
7. Register the new skill in a versioned skill registry
8. Deploy it to staging or production based on risk
9. Execute the task and store the procedural memory

This is how MYCA "learns immediately" without turning the company
into a science experiment with admin privileges.

Architecture: March 9, 2026
"""

from importlib import import_module

__all__: list[str] = []


def _safe_import(module_path: str, symbol: str):
    try:
        module = import_module(module_path, package=__name__)
        obj = getattr(module, symbol)
        globals()[symbol] = obj
        if symbol not in __all__:
            __all__.append(symbol)
        return obj
    except Exception:
        return None


_safe_import(".foundry", "CapabilityFoundry")
_safe_import(".discovery", "CapabilityDiscovery")
_safe_import(".evaluator", "CapabilityEvaluator")
