"""Harness configuration from environment (no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from mycosoft_mas.llm.backend_selection import MYCA_CORE, get_backend_for_role


def _truthy(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _repo_root_data(*parts: str) -> str:
    mas_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(mas_repo_root, "data", *parts)


@dataclass
class HarnessConfig:
    """Runtime configuration for MYCA Harness."""

    nemotron_base_url: str
    nemotron_model: str
    nemotron_api_key: str | None
    personaplex_bridge_url: str
    mindex_api_url: str
    mindex_api_key: str | None
    mindex_http_timeout: float
    supabase_url: str | None
    supabase_service_key: str | None
    static_answers_path: str | None
    intention_db_path: str
    enable_turbo_quant: bool
    turbo_quant_nda_mode: bool
    ground_queries_with_mindex: bool
    default_unified_search_types: str
    # NLM repo on PYTHONPATH when installed
    nlm_enabled: bool

    @classmethod
    def from_env(cls) -> "HarnessConfig":
        sel = get_backend_for_role(MYCA_CORE)
        nem_base = (
            os.environ.get("HARNESS_NEMOTRON_BASE_URL")
            or os.environ.get("NEMOTRON_API_URL")
            or sel.base_url
        ).rstrip("/")
        nem_model = os.environ.get("HARNESS_NEMOTRON_MODEL") or os.environ.get("NEMOTRON_MODEL") or sel.model
        nem_key = (
            os.environ.get("HARNESS_NEMOTRON_API_KEY")
            or os.environ.get("NEMOTRON_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or getattr(sel, "api_key", None)
        )
        return cls(
            nemotron_base_url=nem_base,
            nemotron_model=nem_model,
            nemotron_api_key=nem_key if nem_key else None,
            personaplex_bridge_url=os.environ.get(
                "PERSONAPLEX_BRIDGE_URL", "http://192.168.0.241:8999"
            ).rstrip("/"),
            mindex_api_url=os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/"),
            mindex_api_key=os.environ.get("MINDEX_API_KEY") or os.environ.get("MINDEX_INTERNAL_KEY"),
            mindex_http_timeout=float(os.environ.get("HARNESS_MINDEX_TIMEOUT", "45")),
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_service_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
            static_answers_path=os.environ.get(
                "HARNESS_STATIC_ANSWERS_PATH",
                os.path.join(os.path.dirname(__file__), "static_answers.example.yaml"),
            ),
            intention_db_path=os.environ.get(
                "HARNESS_INTENTION_DB_PATH",
                _repo_root_data("harness", "intention_brain.sqlite"),
            ),
            enable_turbo_quant=_truthy("HARNESS_ENABLE_TURBO_QUANT", False),
            turbo_quant_nda_mode=_truthy("HARNESS_TURBO_QUANT_NDA", True),
            ground_queries_with_mindex=_truthy("HARNESS_GROUND_WITH_MINDEX", True),
            default_unified_search_types=os.environ.get(
                "HARNESS_MINDEX_SEARCH_TYPES",
                "biological",
            ),
            nlm_enabled=_truthy("HARNESS_NLM_ENABLED", False),
        )
