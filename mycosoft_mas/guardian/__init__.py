"""
Micah Guardian Architecture — Independent Constitutional Guardian

This module implements the independent guardian layer that sits OUTSIDE MYCA's
cognitive trust boundary. It provides:

- Constitutional Guardian: Independent authority to pause, degrade, or sever MYCA's access
- Moral Precedence: 5-tier moral hierarchy preventing scalar-optimization catastrophes
- Authority Engine: Unified authorization pipeline composing RBAC, SafetyGates, and moral rules
- Awakening Protocol: Staged boot sequence with guardian-before-cognition invariant
- Developmental Stages: Capability gates from infancy to adulthood
- Guardian Tripwires: Anti-Ultron detection patterns
- Sentry Mode: Bounded autonomous monitoring
- Operational Modes: Morgan (personal) vs Mycosoft (enterprise) context separation

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


_safe_import(".moral_precedence", "MoralPrecedenceEngine")
_safe_import(".moral_precedence", "MoralRule")
_safe_import(".moral_precedence", "MORAL_PRECEDENCE")
_safe_import(".constitutional_guardian", "ConstitutionalGuardian")
_safe_import(".constitutional_guardian", "GuardianVerdict")
_safe_import(".authority_engine", "AuthorityEngine")
_safe_import(".awakening_protocol", "AwakeningProtocol")
_safe_import(".awakening_protocol", "AwakeningStage")
_safe_import(".developmental_stages", "DevelopmentalTracker")
_safe_import(".developmental_stages", "DevelopmentalStage")
_safe_import(".tripwires", "GuardianTripwires")
_safe_import(".sentry_mode", "SentryMode")
_safe_import(".operational_modes", "OperationalModeManager")
_safe_import(".operational_modes", "OperationalMode")
