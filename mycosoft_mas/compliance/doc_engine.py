"""
Multi-model compliance document pipeline: Perplexity → Claude → OpenAI → Postgres.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _db_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def run_compliance_doc_pipeline(*, doc_type: str, title: str) -> Dict[str, Any]:
    """
    Refresh control state, optionally call Perplexity/Claude/OpenAI, insert compliance_docs row.
    Missing API keys skip that stage; body is still versioned from control snapshot JSON.
    """
    if not _db_ready():
        raise RuntimeError("MINDEX_DATABASE_URL not configured")

    from mycosoft_mas.compliance.control_state import refresh_control_state_from_signals
    from mycosoft_mas.integrations.anthropic_client import AnthropicClient
    from mycosoft_mas.integrations.openai_client import OpenAIClient
    from mycosoft_mas.integrations.perplexity_client import PerplexityClient
    from mycosoft_mas.soc import repository as soc_repo

    ctrl = await refresh_control_state_from_signals()
    controls = await soc_repo.list_compliance_controls()

    model_versions: Dict[str, Any] = {"control_refresh": ctrl}

    research: Optional[str] = None
    ppx = PerplexityClient()
    try:
        research = await ppx.chat(
            [
                {
                    "role": "user",
                    "content": (
                        f"Summarize current NIST 800-171 / CMMC expectations for {doc_type} "
                        f"with 5 bullet citations (no fabricated URLs; cite regulation names only). "
                        f"Context: Mycosoft operates a private LAN SOC with device inventory and incidents."
                    ),
                }
            ],
            temperature=0.1,
        )
        model_versions["perplexity"] = "llama-3.1-sonar-small-128k-online"
    except Exception as e:
        logger.warning("Perplexity stage skipped: %s", e)
        model_versions["perplexity"] = "skipped"

    ctrl_json = str(controls)[:12000]
    draft_prompt = (
        f"You are a compliance author. Draft a {doc_type} section in Markdown.\n"
        f"Title: {title}\n"
        f"Research notes:\n{research or '(no live research — use standard NIST 800-171 language)'}\n"
        f"Control snapshot (truncated JSON):\n```\n{ctrl_json}\n```\n"
        "Output only Markdown body (no YAML front matter)."
    )
    anth = AnthropicClient()
    draft = await anth.chat(draft_prompt, model="claude-3-5-sonnet-20241022")
    model_versions["anthropic"] = "claude-3-5-sonnet-20241022" if draft else "skipped"

    review_prompt = (
        "Review the following SSP/POA&M markdown for clarity and internal consistency. "
        "Return: (1) a short executive summary paragraph, (2) '---REVIEW---', (3) revised full markdown.\n\n"
        + (draft or "# Draft unavailable\n_Control state only; configure ANTHROPIC_API_KEY for authoring._\n")
    )
    oai = OpenAIClient()
    reviewed = await oai.chat(
        [{"role": "user", "content": review_prompt}],
        model="gpt-4o-mini",
        temperature=0.2,
    )
    model_versions["openai"] = "gpt-4o-mini" if reviewed else "skipped"

    body = reviewed or draft or f"# {title}\n\n_Authoring keys not fully configured._\n"
    row = await soc_repo.insert_compliance_doc(
        doc_type=doc_type,
        title=title,
        body_md=body,
        model_versions=model_versions,
        approved_by=None,
    )
    return {"status": "ok", "doc": row, "stages": model_versions}
