"""
NLM training / mutation / grounding persistence — NAS JSONL + optional MINDEX SQL.

Change logs are append-only. Never invents metrics.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.nlm.merkle_attest import attest_payloads

logger = logging.getLogger(__name__)

DEFAULT_NAS_RUNS = "/mnt/mycosoft-nas/models/nlm/training_runs"
MINDEX_BASE = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")


def _runs_root() -> Path:
    env = (os.getenv("NLM_TRAINING_STORE_DIR") or "").strip()
    if env:
        return Path(env)
    nas = Path(os.getenv("NLM_HOME", DEFAULT_NAS_RUNS))
    candidate = nas / "training_runs" if nas.name != "training_runs" else nas
    if candidate.exists() or os.name != "nt":
        # Prefer explicit NAS tree when mounted
        nas_explicit = Path(DEFAULT_NAS_RUNS)
        if nas_explicit.parent.exists() or os.getenv("NLM_HOME"):
            return Path(os.getenv("NLM_HOME", str(nas_explicit.parent))) / "training_runs"
        return candidate
    return Path.home() / ".mycosoft" / "nlm" / "training_runs"


def _ensure() -> Path:
    root = _runs_root()
    root.mkdir(parents=True, exist_ok=True)
    for name in (
        "runs.jsonl",
        "mutations.jsonl",
        "change_log.jsonl",
        "grounding.jsonl",
        "agent_tasks.jsonl",
    ):
        path = root / name
        if not path.exists():
            path.write_text("", encoding="utf-8")
    return root


def _append(name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    root = _ensure()
    path = root / name
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return row


def _read_jsonl(name: str, *, limit: int = 100) -> List[Dict[str, Any]]:
    root = _runs_root()
    path = root / name
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(rows) >= max(1, min(limit, 1000)):
            break
    return rows


def _mindex_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = (
        os.getenv("MINDEX_INTERNAL_TOKEN")
        or (os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0] or "")
    ).strip()
    key = (os.getenv("MINDEX_API_KEY") or os.getenv("MINDEX_INTERNAL_KEY") or "").strip()
    if token:
        headers["X-Internal-Token"] = token
    if key:
        headers["X-API-Key"] = key
    return headers


async def _mindex_upsert_run(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort SQL mirror via MINDEX NLM training endpoint when available."""
    url = f"{MINDEX_BASE}/nlm/training/runs"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=run, headers=_mindex_headers())
            if response.status_code in (200, 201):
                return response.json()
            # Fallback: embed into nature_embeddings packet
            nmf_url = f"{MINDEX_BASE}/nlm/nmf"
            packet = {
                "kind": "nlm_training_run",
                "schema": "nlm-training-store/sep23-2026",
                "payload": run,
            }
            response = await client.post(
                nmf_url,
                json={
                    "source_id": run.get("run_id") or f"nlm-run-{uuid.uuid4().hex[:10]}",
                    "anomaly_score": 0.0,
                    "packet": packet,
                },
                headers=_mindex_headers(),
            )
            if response.status_code in (200, 201):
                return response.json()
    except Exception as exc:
        logger.debug("MINDEX training upsert skipped: %s", exc)
    return None


def changelog(
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "change_id": f"chg_{uuid.uuid4().hex[:12]}",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "detail": detail or {},
        "ts": datetime.now(timezone.utc).isoformat(),
        "model_kind": "nature_learning_model",
    }
    return _append("change_log.jsonl", row)


async def persist_run(run: Dict[str, Any]) -> Dict[str, Any]:
    row = {
        **run,
        "persisted_at": datetime.now(timezone.utc).isoformat(),
        "storage": str(_ensure()).replace("\\", "/"),
    }
    _append("runs.jsonl", row)
    changelog(
        entity_type="training_run",
        entity_id=str(run.get("run_id")),
        action="upsert",
        detail={"status": run.get("status")},
    )
    mindex = await _mindex_upsert_run(row)
    return {"ok": True, "run": row, "mindex": mindex}


async def persist_mutation(mutation: Dict[str, Any]) -> Dict[str, Any]:
    row = {
        **mutation,
        "persisted_at": datetime.now(timezone.utc).isoformat(),
    }
    _append("mutations.jsonl", row)
    changelog(
        entity_type="mutation",
        entity_id=str(mutation.get("id") or mutation.get("mutation_id")),
        action="apply",
        detail={"type": mutation.get("type"), "run_id": mutation.get("run_id")},
    )
    return {"ok": True, "mutation": row}


async def persist_grounding(record: Dict[str, Any]) -> Dict[str, Any]:
    """Merkle/ECDSA grounding record for training artifacts / frames."""
    payloads = [record]
    attestation = attest_payloads(payloads, producer_id="mas-nlm-grounding")
    row = {
        "grounding_id": f"gnd_{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "record": record,
        "sha256_leaf": (attestation.get("leaves") or [None])[0],
        "merkle_root": attestation.get("merkle_root"),
        "signature": attestation.get("signature"),
        "inclusion_proofs": attestation.get("inclusion_proofs"),
        "zk_proof": None,
        "zk_note": attestation.get("zk_note"),
        "model_kind": "nature_learning_model",
    }
    _append("grounding.jsonl", row)
    changelog(
        entity_type="grounding",
        entity_id=row["grounding_id"],
        action="attest",
        detail={"merkle_root": row["merkle_root"]},
    )
    return {"ok": True, "grounding": row}


def list_runs(*, limit: int = 50) -> Dict[str, Any]:
    rows = _read_jsonl("runs.jsonl", limit=limit)
    # Deduplicate by run_id keeping newest
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in rows:
        rid = row.get("run_id")
        if rid in seen:
            continue
        seen.add(rid)
        deduped.append(row)
    return {
        "status": "ok",
        "empty": len(deduped) == 0,
        "count": len(deduped),
        "runs": deduped,
        "store": str(_runs_root()).replace("\\", "/"),
        "message": None if deduped else "No training runs persisted yet.",
        "model_kind": "nature_learning_model",
    }


def latest_run() -> Dict[str, Any]:
    listing = list_runs(limit=20)
    runs = listing.get("runs") or []
    if not runs:
        return {
            "status": "ok",
            "empty": True,
            "run": None,
            "message": "No training runs yet.",
            "model_kind": "nature_learning_model",
        }
    return {
        "status": "ok",
        "empty": False,
        "run": runs[0],
        "model_kind": "nature_learning_model",
    }


def list_mutations(*, limit: int = 50, run_id: Optional[str] = None) -> Dict[str, Any]:
    rows = _read_jsonl("mutations.jsonl", limit=limit * 2)
    if run_id:
        rows = [r for r in rows if r.get("run_id") == run_id][:limit]
    else:
        rows = rows[:limit]
    return {
        "status": "ok",
        "empty": len(rows) == 0,
        "count": len(rows),
        "mutations": rows,
        "message": None if rows else "No mutations recorded.",
        "model_kind": "nature_learning_model",
    }


def list_change_log(*, limit: int = 100) -> Dict[str, Any]:
    rows = _read_jsonl("change_log.jsonl", limit=limit)
    return {
        "status": "ok",
        "empty": len(rows) == 0,
        "count": len(rows),
        "changes": rows,
        "model_kind": "nature_learning_model",
    }


def list_grounding(*, limit: int = 50) -> Dict[str, Any]:
    rows = _read_jsonl("grounding.jsonl", limit=limit)
    return {
        "status": "ok",
        "empty": len(rows) == 0,
        "count": len(rows),
        "groundings": rows,
        "message": None if rows else "No grounding records yet.",
        "model_kind": "nature_learning_model",
    }
