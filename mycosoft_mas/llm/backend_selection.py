"""
Unified backend-selection contract for MAS LLM routing.

All model entry points (LLMRouter, FrontierLLMRouter, LLMBrain) should resolve
backend and model via get_backend_for_role(role) so Nemotron and other backends
are configured in one place. See docs/UNIFIED_LLM_ROUTING_NEMOTRON_MAR14_2026.md.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

# Model roles for unified routing (Nemotron MYCA rollout)
ModelRole = str  # use literals for clarity in callers

# Canonical role names
NEMOTRON_SUPER = "nemotron_super"
NEMOTRON_NANO = "nemotron_nano"
NEMOTRON_ULTRA = "nemotron_ultra"
NEMOTRON_SPEECH = "nemotron_speech"
NEMOTRON_SAFETY = "nemotron_safety"
NEMOTRON_RAG = "nemotron_rag"
MYCA_CORE = "myca_core"
MYCA_EDGE = "myca_edge"
# MYCA2 sandbox roles — registry alias resolution checked first (MINDEX plasticity)
MYCA2_CORE = "myca2_core"
MYCA2_EDGE = "myca2_edge"
MYCA2_SANDBOX = "myca2_sandbox"
PSILO_OVERLAY = "psilo_overlay"
_MYCA2_ROLES = frozenset({MYCA2_CORE, MYCA2_EDGE, MYCA2_SANDBOX, PSILO_OVERLAY})
# Task-type roles (used by LLMRouter)
PLANNING = "planning"
EXECUTION = "execution"
FAST = "fast"
EMBEDDING = "embedding"
FALLBACK = "fallback"

# Category identifiers used by migration toggles.
_CATEGORY_CORPORATE = "corporate"
_CATEGORY_INFRA = "infrastructure"
_CATEGORY_DEVICE = "device"
_CATEGORY_ROUTE = "route"
_CATEGORY_NLM = "nlm"
_CATEGORY_CONSCIOUSNESS = "consciousness"

_MODE_HYBRID = "hybrid"
_MODE_NEMOTRON = "nemotron"
_MODE_LLAMA = "llama"


def resolve_nemotron_base_url() -> str:
    """
    OpenAI-compatible Nemotron on the same host as MAS (VM 188 or dev machine).

    Set NEMOTRON_BASE_URL to override (remote GPU, Docker hostname, etc.).
    If unset, defaults to http://127.0.0.1:NEMOTRON_HTTP_PORT (default port 11434,
    Ollama OpenAI-compatible API on the MAS VM). Use 11435+ if you run a dedicated vLLM/Nemotron server.
    """
    if os.getenv("NEMOTRON_DISABLE_LOCAL_DEFAULT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return os.getenv("NEMOTRON_BASE_URL", "").strip()
    explicit = os.getenv("NEMOTRON_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = (os.getenv("NEMOTRON_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    port = (os.getenv("NEMOTRON_HTTP_PORT") or "11434").strip() or "11434"
    return f"http://{host}:{port}"
_VALID_MODES = frozenset({_MODE_HYBRID, _MODE_NEMOTRON, _MODE_LLAMA})


@dataclass
class BackendSelection:
    """Resolved backend for a given role.

    When a deployment bundle is active for the target alias, cache_mode and
    serving_profile_id are populated from the bundle's serving profile.
    """

    provider: str
    base_url: str
    model: str
    api_key: str = ""
    # KVTC serving lane fields (populated when bundle is active)
    cache_mode: str = "baseline"
    serving_profile_id: str = ""
    deployment_bundle_id: str = ""
    kvtc_artifact_id: str = ""


def _expand_env(s: str) -> str:
    """Replace ${VAR:-default} style placeholders."""
    if not s or "${" not in s:
        return s
    out = []
    i = 0
    while i < len(s):
        if s[i : i + 2] == "${":
            j = s.find("}", i)
            if j == -1:
                out.append(s[i])
                i += 1
                continue
            expr = s[i + 2 : j]
            if ":-" in expr:
                var, default = expr.split(":-", 1)
                val = os.getenv(var.strip(), default.strip())
            else:
                val = os.getenv(expr.strip(), "")
            out.append(val)
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _load_models_yaml() -> dict:
    """Load config/models.yaml if present."""
    for base in (Path.cwd(), Path(__file__).resolve().parent.parent.parent):
        path = base / "config" / "models.yaml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
                return data
    return {}


def _infer_role_category(role: str) -> str:
    """Infer a backend category for role-aware migration toggles."""
    role_l = (role or "").strip().lower()
    if role_l in {
        MYCA_CORE,
        MYCA2_CORE,
        MYCA2_SANDBOX,
        PLANNING,
        EXECUTION,
        FAST,
        FALLBACK,
    }:
        return _CATEGORY_CORPORATE
    if role_l in {EMBEDDING, "nlm", "rag", "retrieval"}:
        return _CATEGORY_NLM
    if role_l in {MYCA_EDGE, MYCA2_EDGE, PSILO_OVERLAY}:
        return _CATEGORY_DEVICE

    if any(k in role_l for k in ("device", "mycobrain", "telemetry", "sensor", "gateway")):
        return _CATEGORY_DEVICE
    if any(k in role_l for k in ("infra", "deployment", "ops", "security", "docker", "proxmox")):
        return _CATEGORY_INFRA
    if any(k in role_l for k in ("route", "router", "routing", "route_monitor", "dispatch")):
        return _CATEGORY_ROUTE
    if any(k in role_l for k in ("conscious", "intention", "memory", "brain", "reflection", "grounding")):
        return _CATEGORY_CONSCIOUSNESS
    if any(k in role_l for k in ("nlm", "embed", "retriev", "rag")):
        return _CATEGORY_NLM
    return _CATEGORY_CORPORATE


def _get_backend_mode(role: str) -> str:
    """
    Resolve backend mode for a role.

    Global mode can be set with MYCA_BACKEND_MODE=hybrid|nemotron|llama.
    Per-category overrides are available through:
    - MYCA_BACKEND_MODE_CORPORATE
    - MYCA_BACKEND_MODE_INFRA
    - MYCA_BACKEND_MODE_DEVICE
    - MYCA_BACKEND_MODE_ROUTE
    - MYCA_BACKEND_MODE_NLM
    - MYCA_BACKEND_MODE_CONSCIOUSNESS
    """
    global_mode = os.getenv("MYCA_BACKEND_MODE", _MODE_HYBRID).strip().lower()
    if global_mode not in _VALID_MODES:
        global_mode = _MODE_HYBRID

    category = _infer_role_category(role)
    category_env_map = {
        _CATEGORY_CORPORATE: "MYCA_BACKEND_MODE_CORPORATE",
        _CATEGORY_INFRA: "MYCA_BACKEND_MODE_INFRA",
        _CATEGORY_DEVICE: "MYCA_BACKEND_MODE_DEVICE",
        _CATEGORY_ROUTE: "MYCA_BACKEND_MODE_ROUTE",
        _CATEGORY_NLM: "MYCA_BACKEND_MODE_NLM",
        _CATEGORY_CONSCIOUSNESS: "MYCA_BACKEND_MODE_CONSCIOUSNESS",
    }
    override_name = category_env_map.get(category, "")
    if override_name:
        override_mode = os.getenv(override_name, "").strip().lower()
        if override_mode in _VALID_MODES:
            return override_mode
    return global_mode


def _resolve_nemotron_model_for_role(role: str) -> str:
    """Resolve per-category Nemotron model override."""
    category = _infer_role_category(role)
    env_key_by_category = {
        _CATEGORY_CORPORATE: "NEMOTRON_MODEL_CORPORATE",
        _CATEGORY_INFRA: "NEMOTRON_MODEL_INFRA",
        _CATEGORY_DEVICE: "NEMOTRON_MODEL_DEVICE",
        _CATEGORY_ROUTE: "NEMOTRON_MODEL_ROUTE",
        _CATEGORY_NLM: "NEMOTRON_MODEL_NLM",
        _CATEGORY_CONSCIOUSNESS: "NEMOTRON_MODEL_CONSCIOUSNESS",
    }
    env_key = env_key_by_category.get(category, "")
    if env_key and os.getenv(env_key):
        return _expand_env(os.getenv(env_key, "").strip())
    if role in (NEMOTRON_NANO, MYCA_EDGE, MYCA2_EDGE, PSILO_OVERLAY):
        return _expand_env(os.getenv("NEMOTRON_MODEL_NANO", "nemotron-nano"))
    return _expand_env(os.getenv("NEMOTRON_MODEL_SUPER", "nemotron-super"))


def _forced_selection_for_mode(role: str, mode: str) -> BackendSelection | None:
    """
    Build forced BackendSelection for explicit backend mode.

    hybrid -> None (use normal role resolution)
    nemotron -> force OpenAI-compatible Nemotron endpoint if configured
    llama -> force Ollama/Llama endpoint
    """
    if mode == _MODE_HYBRID:
        return None

    ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    if mode == _MODE_LLAMA:
        return BackendSelection(
            provider="ollama",
            base_url=ollama_url.rstrip("/"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            api_key="",
        )

    nemotron_base = resolve_nemotron_base_url()
    if mode == _MODE_NEMOTRON and nemotron_base:
        return BackendSelection(
            provider="nemotron",
            base_url=nemotron_base.rstrip("/"),
            model=_resolve_nemotron_model_for_role(role),
            api_key=os.getenv("NEMOTRON_API_KEY", ""),
        )

    # If Nemotron is forced but local default disabled and no URL, fail closed to local Llama.
    if mode == _MODE_NEMOTRON:
        return BackendSelection(
            provider="ollama",
            base_url=ollama_url.rstrip("/"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            api_key="",
        )
    return None


def get_role_category(role: ModelRole) -> str:
    """Public helper used by telemetry and tests."""
    return _infer_role_category(role)


def get_backend_mode_for_role(role: ModelRole) -> str:
    """Public helper used by telemetry and tests."""
    return _get_backend_mode(role)


def get_backend_for_role(role: ModelRole) -> BackendSelection:
    """
    Resolve the backend (provider, base_url, model) for a given role.
    MYCA2 roles: MINDEX plasticity alias -> candidate (artifact_uri as base_url) first; then models.yaml.
    """
    data = _load_models_yaml()
    providers = data.get("providers") or {}
    roles = data.get("roles") or {}
    model_roles = data.get("model_roles") or {}

    if role in _MYCA2_ROLES:
        # First: check for active deployment bundle (KVTC-aware)
        try:
            from mycosoft_mas.serving.bundle_manager import get_bundle_manager
            from mycosoft_mas.serving.profile_manager import get_profile_manager

            bm = get_bundle_manager()
            bundle = bm.get_active_bundle(role)
            if bundle:
                pm = get_profile_manager()
                profile = pm.get_profile(bundle.serving_profile_id)
                cache_mode = profile.cache_mode.value if profile else "baseline"
                artifact_ref = str(profile.artifact_ref) if profile and profile.artifact_ref else ""

                # Resolve base_url from plasticity registry for the underlying model
                from mycosoft_mas.integrations.plasticity_registry import resolve_alias_to_backend_spec
                spec = resolve_alias_to_backend_spec(role)
                bu = (spec or {}).get("base_url") or ""
                if bu.strip():
                    return BackendSelection(
                        provider="openai_compatible",
                        base_url=bu.rstrip("/"),
                        model=str((spec or {}).get("model") or "default").strip(),
                        api_key=_expand_env(os.getenv("NEMOTRON_API_KEY", "")),
                        cache_mode=cache_mode,
                        serving_profile_id=str(bundle.serving_profile_id),
                        deployment_bundle_id=str(bundle.deployment_bundle_id),
                        kvtc_artifact_id=artifact_ref,
                    )
        except Exception:
            pass

        # Fallback: plasticity registry without bundle
        try:
            from mycosoft_mas.integrations.plasticity_registry import resolve_alias_to_backend_spec

            spec = resolve_alias_to_backend_spec(role)
            bu = (spec or {}).get("base_url") or ""
            if bu.strip():
                return BackendSelection(
                    provider="openai_compatible",
                    base_url=bu.rstrip("/"),
                    model=str((spec or {}).get("model") or "default").strip(),
                    api_key=_expand_env(os.getenv("NEMOTRON_API_KEY", "")),
                )
        except Exception:
            pass

    mode = _get_backend_mode(role)
    forced = _forced_selection_for_mode(role, mode)
    if forced is not None:
        return forced

    # Aliases: myca_core -> nemotron_super or local/ollama when Nemotron not set
    role_key = role
    if role == MYCA_CORE:
        role_key = roles.get("myca_core") or roles.get("nemotron_super") or "local"
    elif role == MYCA_EDGE:
        role_key = roles.get("myca_edge") or roles.get("nemotron_nano") or "local"
    elif role == MYCA2_CORE:
        role_key = "myca2_core"
    elif role == MYCA2_EDGE:
        role_key = "myca2_edge"
    elif role == MYCA2_SANDBOX:
        role_key = "myca2_sandbox"
    elif role == PSILO_OVERLAY:
        role_key = "psilo_overlay"

    # Role in YAML can be "provider:model" or a key under model_roles
    role_spec = (
        model_roles.get(role) or model_roles.get(role_key) or roles.get(role) or roles.get(role_key)
    )

    if isinstance(role_spec, str) and ":" in role_spec:
        prov_name, model = role_spec.split(":", 1)
        prov_name = prov_name.strip()
        model = _expand_env(model.strip())
        # Resolve provider config from providers section
        prov_cfg = providers.get(prov_name) or {}
        base_url = _expand_env(prov_cfg.get("base_url") or "")
        api_key = _expand_env(prov_cfg.get("api_key") or "")
        if not base_url and prov_name == "local":
            base_url = os.getenv("LLM_BASE_URL", "http://localhost:4000")
        if not base_url and prov_name == "nemotron":
            base_url = resolve_nemotron_base_url()
        if not base_url and prov_name == "ollama":
            base_url = os.getenv(
                "OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")
            )
        default_url = "http://localhost:11434"
        if prov_name == "nemotron":
            default_url = resolve_nemotron_base_url() or "http://127.0.0.1:11434"
        elif prov_name == "local":
            default_url = os.getenv("LLM_BASE_URL", "http://localhost:4000")
        return BackendSelection(
            provider=prov_name,
            base_url=(base_url or default_url).rstrip("/"),
            model=model,
            api_key=api_key,
        )

    # No YAML role spec: use env-based defaults
    nemotron_base = resolve_nemotron_base_url()
    if role in (NEMOTRON_SUPER, MYCA_CORE, MYCA2_CORE, MYCA2_SANDBOX):
        if nemotron_base:
            return BackendSelection(
                provider="nemotron",
                base_url=nemotron_base.rstrip("/"),
                model=_expand_env(os.getenv("NEMOTRON_MODEL_SUPER", "nemotron-super")),
                api_key=os.getenv("NEMOTRON_API_KEY", ""),
            )
        ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        return BackendSelection(
            provider="ollama",
            base_url=ollama_url.rstrip("/"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            api_key="",
        )
    if role in (NEMOTRON_NANO, MYCA_EDGE, MYCA2_EDGE, PSILO_OVERLAY):
        if nemotron_base:
            return BackendSelection(
                provider="nemotron",
                base_url=nemotron_base.rstrip("/"),
                model=_expand_env(os.getenv("NEMOTRON_MODEL_NANO", "nemotron-nano")),
                api_key=os.getenv("NEMOTRON_API_KEY", ""),
            )
        ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        return BackendSelection(
            provider="ollama",
            base_url=ollama_url.rstrip("/"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            api_key="",
        )

    # Other roles (planning, execution, fast, embedding, fallback): default to Ollama
    ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    return BackendSelection(
        provider="ollama",
        base_url=ollama_url.rstrip("/"),
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        api_key="",
    )
