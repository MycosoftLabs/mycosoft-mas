"""
Unified backend-selection contract for MAS LLM routing.

All model entry points (LLMRouter, FrontierLLMRouter, LLMBrain) should resolve
backend and model via get_backend_for_role(role) so Nemotron and other backends
are configured in one place. See docs/UNIFIED_LLM_ROUTING_NEMOTRON_MAR14_2026.md.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
# Task-type roles (used by LLMRouter)
PLANNING = "planning"
EXECUTION = "execution"
FAST = "fast"
EMBEDDING = "embedding"
FALLBACK = "fallback"


@dataclass
class BackendSelection:
    """Resolved backend for a given role."""
    provider: str
    base_url: str
    model: str
    api_key: str = ""


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


def get_backend_for_role(role: ModelRole) -> BackendSelection:
    """
    Resolve the backend (provider, base_url, model) for a given role.
    Used by LLMRouter, FrontierLLMRouter, and LLMBrain for unified routing.
    """
    data = _load_models_yaml()
    providers = data.get("providers") or {}
    roles = data.get("roles") or {}

    # Aliases: myca_core -> nemotron_super or local/ollama when Nemotron not set
    role_key = role
    if role == MYCA_CORE:
        role_key = roles.get("myca_core") or roles.get("nemotron_super") or "local"
    elif role == MYCA_EDGE:
        role_key = roles.get("myca_edge") or roles.get("nemotron_nano") or "local"

    # Role in YAML can be "provider:model" or a key under model_roles
    model_roles = data.get("model_roles") or {}
    role_spec = model_roles.get(role) or model_roles.get(role_key) or roles.get(role) or roles.get(role_key)

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
            base_url = os.getenv("NEMOTRON_BASE_URL", "")
        if not base_url and prov_name == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        return BackendSelection(
            provider=prov_name,
            base_url=(base_url or "http://localhost:11434").rstrip("/"),
            model=model,
            api_key=api_key,
        )

    # No YAML role spec: use env-based defaults
    nemotron_base = os.getenv("NEMOTRON_BASE_URL", "").strip()
    if role in (NEMOTRON_SUPER, MYCA_CORE):
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
    if role in (NEMOTRON_NANO, MYCA_EDGE):
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
