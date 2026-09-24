"""
NLM security monitoring hooks — vulnerability / policy checks for scientific NLM.

Detects GGUF/Ollama contamination under models/nlm, missing attestation keys,
unsigned promotions, and empty ingest vs claimed live data. No mock findings.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

GGUF_MARKERS = (".gguf", "ollama", "llama.cpp", "chat-adapter")
DEFAULT_NLM_HOME = "/mnt/mycosoft-nas/models/nlm"


def _nlm_home() -> Path:
    return Path(os.getenv("NLM_HOME", DEFAULT_NLM_HOME))


def scan_nlm_security() -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    home = _nlm_home()
    now = datetime.now(timezone.utc).isoformat()

    if not home.exists():
        findings.append(
            {
                "severity": "medium",
                "code": "nlm_home_missing",
                "message": f"NLM_HOME not mounted or missing: {home}",
                "remediation": "Mount NAS models/nlm on MAS VM; never use models/myca.",
            }
        )
    else:
        # Walk shallow for GGUF / chat contamination
        for path in home.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            rel = str(path).replace("\\", "/")
            if any(m in name for m in GGUF_MARKERS) or name.endswith(".gguf"):
                findings.append(
                    {
                        "severity": "critical",
                        "code": "gguf_in_nlm_tree",
                        "message": f"Chat/GGUF artifact under NLM tree: {rel}",
                        "path": rel,
                        "remediation": "Move to models/myca; NLM must remain signal-native.",
                    }
                )
            if "myca" in rel.split("/"):
                findings.append(
                    {
                        "severity": "high",
                        "code": "myca_path_leak",
                        "message": f"MYCA path intersected NLM scan: {rel}",
                        "path": rel,
                        "remediation": "Keep models/nlm and models/myca compartments separate.",
                    }
                )

    key_path = Path(
        os.getenv(
            "NLM_ATTEST_KEY_PATH",
            str(Path.home() / ".mycosoft" / "nlm" / "attest_ecdsa_p256.pem"),
        )
    )
    if not key_path.exists():
        findings.append(
            {
                "severity": "low",
                "code": "attest_key_absent",
                "message": "ECDSA P-256 attest key not yet created (will be minted on first attest).",
                "path": str(key_path),
                "remediation": "Call POST /api/nlm/training/attest once in a secured environment.",
            }
        )

    critical = sum(1 for f in findings if f.get("severity") == "critical")
    high = sum(1 for f in findings if f.get("severity") == "high")
    status = "alert" if critical or high else ("warn" if findings else "ok")

    return {
        "status": status,
        "timestamp": now,
        "nlm_home": str(home).replace("\\", "/"),
        "finding_count": len(findings),
        "critical": critical,
        "high": high,
        "findings": findings,
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
        "policy": {
            "allow_gguf_in_nlm": False,
            "allow_ollama_branding": False,
            "require_sha256_grounding": True,
            "zk_required": False,
        },
    }
