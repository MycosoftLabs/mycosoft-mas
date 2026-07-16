"""Fail-closed CUI and secret guard for every Mycosoft MAS agent.

Policy source:
    AI_AGENT_CUI_RULES_OF_BEHAVIOR_JUL15_2026.md
Policy SHA-256:
    350442fb938e5e14114817e7ddfc08a16ecb84bf3a50b705977b4a68655beb19

When a payload is blocked, this module records only a SHA-256 fingerprint,
rule identifiers, source, and byte length. It never logs suspected CUI or a
secret itself.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import re
from dataclasses import dataclass, field
from functools import wraps
from types import MethodType
from typing import Any, Callable, Iterable, Mapping

logger = logging.getLogger("mycosoft.cui_guard")

POLICY_ID = "MYC-CUI-AI-ROB-1.0"
POLICY_VERSION = "1.0"
POLICY_DATE = "2026-07-15"
POLICY_SHA256 = "350442fb938e5e14114817e7ddfc08a16ecb84bf3a50b705977b4a68655beb19"
POLICY_OWNER = "Morgan Rockcoons (SAO)"
AUTHORIZED_CUI_SYSTEM = "PreVeil"

OUTSIDE_BOUNDARY_SYSTEMS = frozenset(
    {
        "chatgpt",
        "openai-commercial",
        "claude-commercial",
        "anthropic-commercial",
        "cursor",
        "cursor-cloud",
        "perplexity",
        "gemini-commercial",
        "github",
        "google-drive",
        "google-workspace",
        "gmail",
        "slack",
        "notion",
        "asana",
        "supabase",
        "copilot",
        "myca-commercial-inference",
    }
)

# Bare policy terminology such as "CUI handling" is allowed. Markings and
# explicit classification metadata are blocked.
_CUI_TEXT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CUI_MARKING", re.compile(r"\bCUI//(?:[A-Z0-9_-]+(?:/[A-Z0-9_-]+)*)", re.IGNORECASE)),
    (
        "CUI_BANNER",
        re.compile(
            r"CONTROLLED\s+UNCLASSIFIED\s+INFORMATION.{0,160}(?:CONTROLLED\s+BY|CUI\s+CATEGORY|LIMITED\s+DISSEMINATION)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    ("EXPORT_CONTROLLED_MARKING", re.compile(r"\b(?:ITAR|EAR)\s+(?:CONTROLLED|RESTRICTED)\b", re.IGNORECASE)),
    ("DISTRIBUTION_STATEMENT", re.compile(r"\bDISTRIBUTION\s+STATEMENT\s+[B-F]\b", re.IGNORECASE)),
)

_SECRET_TEXT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GENERIC_BEARER", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{24,}=*\b", re.IGNORECASE)),
    (
        "ASSIGNED_SECRET",
        re.compile(
            r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/@-]{12,}",
            re.IGNORECASE,
        ),
    ),
)

_CLASSIFICATION_KEYS = frozenset(
    {
        "classification",
        "data_classification",
        "content_classification",
        "security_classification",
        "handling",
        "handling_level",
    }
)
_BLOCKED_CLASSIFICATION_VALUES = frozenset(
    {
        "cui",
        "cui-basic",
        "cui-specified",
        "cti",
        "cdi",
        "controlled technical information",
        "covered defense information",
        "itar-controlled",
        "ear-controlled",
        "export-controlled",
        "fouo",
    }
)
_TRUE_CUI_KEYS = frozenset({"contains_cui", "is_cui", "cui", "contains_cti", "contains_cdi"})

PASTE_READY_POLICY_BLOCK = (
    "Mycosoft CUI / CMMC L2 Rules of Behavior (mandatory). Mycosoft, LLC is pursuing "
    "CMMC Level 2; do not state that it is CMMC compliant. This commercial/general-purpose "
    "AI or SaaS path is outside the CUI boundary and is not authorized to process CUI. CUI "
    "lives only in PreVeil until Morgan Rockcoons, the SAO, authorizes a named in-boundary "
    "service and adds it to the SSP. Never input, store, summarize, transform, transmit, or "
    "output CUI, CTI, CDI, export-controlled technical data, marked CUI documents, or "
    "covered-contract technical content here. If classification is uncertain, stop and route "
    "the material to PreVeil. Never expose secrets. Never mark a control Met without a real "
    "evidence URI and SAO validation. Humans submit government filings. Use Morgan Rockcoons "
    "(SAO) and RJ Ricasata (CFO); Mycosoft self-performs. If CUI is encountered outside "
    "PreVeil, stop processing, preserve only non-content incident metadata, and alert the SAO."
)


@dataclass(frozen=True)
class GuardFinding:
    rule_id: str
    kind: str
    path: str


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    policy_id: str = POLICY_ID
    policy_sha256: str = POLICY_SHA256
    fingerprint: str = ""
    payload_bytes: int = 0
    findings: tuple[GuardFinding, ...] = field(default_factory=tuple)

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(sorted({finding.rule_id for finding in self.findings}))


class CUIBoundaryViolation(RuntimeError):
    """Raised when content cannot be processed outside the authorized CUI boundary."""

    def __init__(self, decision: GuardDecision, source: str):
        self.decision = decision
        self.source = source
        codes = ",".join(decision.reason_codes) or "UNSPECIFIED"
        super().__init__(
            f"Blocked by {POLICY_ID} at {source}; route suspected CUI/secrets to the authorized path. "
            f"fingerprint={decision.fingerprint} rules={codes}"
        )


def _canonical_bytes(payload: Any) -> bytes:
    try:
        return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    except Exception:
        return repr(payload).encode("utf-8", errors="replace")


def _walk(payload: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            child = f"{path}.{key}"
            yield child, (key, value)
            yield from _walk(value, child)
    elif isinstance(payload, (list, tuple, set, frozenset)):
        for index, value in enumerate(payload):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, payload


def inspect_payload(payload: Any) -> GuardDecision:
    raw = _canonical_bytes(payload)
    findings: list[GuardFinding] = []

    for path, value in _walk(payload):
        if isinstance(value, tuple) and len(value) == 2:
            key, field_value = value
            key_norm = str(key).strip().lower()
            if key_norm in _TRUE_CUI_KEYS and field_value is True:
                findings.append(GuardFinding("EXPLICIT_CUI_FLAG", "cui", path))
            if key_norm in _CLASSIFICATION_KEYS:
                normalized = str(field_value).strip().lower()
                if normalized in _BLOCKED_CLASSIFICATION_VALUES:
                    findings.append(GuardFinding("EXPLICIT_CUI_CLASSIFICATION", "cui", path))
            continue

        if not isinstance(value, str):
            continue

        for rule_id, pattern in _CUI_TEXT_RULES:
            if pattern.search(value):
                findings.append(GuardFinding(rule_id, "cui", path))
        for rule_id, pattern in _SECRET_TEXT_RULES:
            if pattern.search(value):
                findings.append(GuardFinding(rule_id, "secret", path))

    return GuardDecision(
        allowed=not findings,
        fingerprint=hashlib.sha256(raw).hexdigest(),
        payload_bytes=len(raw),
        findings=tuple(findings),
    )


def assert_non_cui(payload: Any, *, source: str) -> GuardDecision:
    decision = inspect_payload(payload)
    if not decision.allowed:
        logger.critical(
            "cui_policy_block source=%s policy=%s policy_sha=%s fingerprint=%s bytes=%s rules=%s",
            source,
            POLICY_ID,
            POLICY_SHA256,
            decision.fingerprint,
            decision.payload_bytes,
            ",".join(decision.reason_codes),
        )
        raise CUIBoundaryViolation(decision, source)
    return decision


def guarded_system_prompt(role_block: str | None = None) -> str:
    return f"{PASTE_READY_POLICY_BLOCK}\n\nRole-specific instruction: {role_block}" if role_block else PASTE_READY_POLICY_BLOCK


def _guarded_bound_method(bound: Callable[..., Any], *, source: str) -> Callable[..., Any]:
    if getattr(bound, "__mycosoft_cui_guarded__", False):
        return bound

    if inspect.iscoroutinefunction(bound):
        @wraps(bound)
        async def async_guarded(*args: Any, **kwargs: Any) -> Any:
            assert_non_cui({"args": args, "kwargs": kwargs}, source=f"{source}.input")
            result = await bound(*args, **kwargs)
            assert_non_cui(result, source=f"{source}.output")
            return result

        async_guarded.__mycosoft_cui_guarded__ = True  # type: ignore[attr-defined]
        return async_guarded

    @wraps(bound)
    def sync_guarded(*args: Any, **kwargs: Any) -> Any:
        assert_non_cui({"args": args, "kwargs": kwargs}, source=f"{source}.input")
        result = bound(*args, **kwargs)
        assert_non_cui(result, source=f"{source}.output")
        return result

    sync_guarded.__mycosoft_cui_guarded__ = True  # type: ignore[attr-defined]
    return sync_guarded


def guard_agent_instance(instance: Any) -> None:
    method_names = (
        "process_task",
        "process_message",
        "_handle_message",
        "_handle_notification",
        "remember",
        "learn_fact",
        "share_with_agents",
        "record_task_completion",
        "record_error",
        "execute_task",
        "send_message",
        "request_from_agent",
        "log_to_mindex",
    )
    for method_name in method_names:
        bound = getattr(instance, method_name, None)
        if not callable(bound) or getattr(bound, "__mycosoft_cui_guarded__", False):
            continue
        wrapped = _guarded_bound_method(
            bound,
            source=f"agent:{getattr(instance, 'agent_id', instance.__class__.__name__)}.{method_name}",
        )
        setattr(instance, method_name, MethodType(wrapped.__func__, instance) if inspect.ismethod(wrapped) else wrapped)


def _patch_agent_class(agent_class: type[Any]) -> None:
    if getattr(agent_class, "__mycosoft_cui_class_guarded__", False):
        return
    original_init = agent_class.__init__

    @wraps(original_init)
    def guarded_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        guard_agent_instance(self)
        setattr(self, "cui_policy_id", POLICY_ID)
        setattr(self, "cui_policy_sha256", POLICY_SHA256)
        setattr(self, "cui_authorized", False)

    agent_class.__init__ = guarded_init  # type: ignore[method-assign]
    agent_class.__mycosoft_cui_class_guarded__ = True  # type: ignore[attr-defined]


_INSTALLED = False


def install_global_agent_guard() -> None:
    """Patch all known base-agent lineages before new agents instantiate."""
    global _INSTALLED
    if _INSTALLED:
        return

    from mycosoft_mas.agents.base_agent import BaseAgent as AgentBase
    from mycosoft_mas.core.base_agent import BaseAgent as CoreBase

    _patch_agent_class(AgentBase)
    _patch_agent_class(CoreBase)

    try:
        from mycosoft_mas.agents.v2.base_agent_v2 import BaseAgentV2
        _patch_agent_class(BaseAgentV2)
    except Exception as exc:  # V2 may not be importable in minimal/test installs.
        logger.warning("CUI guard V2 patch deferred: %s", exc)

    _INSTALLED = True
    logger.warning(
        "Mycosoft CUI guard installed policy=%s sha256=%s authorized_cui_system=%s",
        POLICY_ID,
        POLICY_SHA256,
        AUTHORIZED_CUI_SYSTEM,
    )
