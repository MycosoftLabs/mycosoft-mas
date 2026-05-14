from __future__ import annotations

import json

import pytest

from mycosoft_mas.avani.audit.ledger import (
    AvaniAuditLedger,
    canonical_json,
    compute_entry_hash,
)


class FailingMindexClient:
    async def _get_db_pool(self):
        raise RuntimeError("database unavailable in test")


@pytest.mark.asyncio
async def test_canonical_json_is_stable():
    left = {"b": 2, "a": {"d": 4, "c": 3}}
    right = {"a": {"c": 3, "d": 4}, "b": 2}
    assert canonical_json(left) == canonical_json(right)


@pytest.mark.asyncio
async def test_jsonl_fallback_hash_chain_and_verify(tmp_path):
    ledger = AvaniAuditLedger(mindex_client=FailingMindexClient(), fallback_dir=tmp_path)

    first = await ledger.append(
        event_kind="proposal_evaluation",
        source="test-agent",
        action_type="test",
        decision={"approved": True},
        season="spring",
    )
    second = await ledger.append(
        event_kind="message_evaluation",
        source="user",
        action_type="chat",
        decision={"verdict": "allow"},
        season="spring",
    )

    assert first.storage == "jsonl_fallback"
    assert second.prev_hash == first.entry_hash

    verification = await ledger.verify()
    assert verification.valid
    assert verification.checked == 2


@pytest.mark.asyncio
async def test_jsonl_fallback_detects_tampering(tmp_path):
    ledger = AvaniAuditLedger(mindex_client=FailingMindexClient(), fallback_dir=tmp_path)
    await ledger.append(
        event_kind="proposal_evaluation",
        source="test-agent",
        action_type="test",
        decision={"approved": True},
        season="spring",
    )

    path = next(tmp_path.glob("avani_audit_*.jsonl"))
    raw = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    raw["decision"]["approved"] = False
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    verification = await ledger.verify()
    assert not verification.valid
    assert verification.reason == "entry_hash_mismatch"


def test_compute_entry_hash_excludes_entry_hash_field():
    entry = {
        "event_id": "x",
        "timestamp": "2026-05-14T00:00:00+00:00",
        "event_kind": "proposal_evaluation",
        "source": "test",
        "action_type": "test",
        "decision": {"approved": True},
        "season": "spring",
        "metadata": {},
        "prev_hash": "0" * 64,
        "entry_hash": "ignored",
    }
    without_hash = dict(entry)
    without_hash.pop("entry_hash")
    assert compute_entry_hash(entry) == compute_entry_hash(without_hash)
