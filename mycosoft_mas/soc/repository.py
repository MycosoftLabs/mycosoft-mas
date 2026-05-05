"""
SOC Postgres repository — soc_ops schema (migration 030).
Uses shared palace asyncpg pool (MINDEX_DATABASE_URL).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


async def _pool():
    from mycosoft_mas.memory.palace.db_pool import get_shared_pool

    return await get_shared_pool()


async def append_chain_row(
    conn: Any,
    incident_id: UUID,
    sequence_number: int,
    prev_hash: str,
    event_type: str,
    payload: Dict[str, Any],
) -> int:
    body = json.dumps(payload, sort_keys=True, default=str)
    event_hash = hashlib.sha256(
        f"{prev_hash}|{sequence_number}|{event_type}|{body}".encode()
    ).hexdigest()
    row = await conn.fetchrow(
        """
        INSERT INTO soc_ops.incident_chain
            (incident_id, sequence_number, prev_hash, event_hash, event_type, payload)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id
        """,
        incident_id,
        sequence_number,
        prev_hash,
        event_hash,
        event_type,
        json.dumps(payload),
    )
    return int(row["id"])


async def create_incident(
    title: str,
    description: str,
    severity: str,
    status: str = "open",
    source: Optional[str] = None,
    kind: Optional[str] = None,
    source_ip: Optional[str] = None,
    host: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    pool = await _pool()
    details = details or {}
    tags = tags or []
    timeline = timeline or []
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO soc_ops.security_incidents
                (title, description, severity, status, source, kind, source_ip, host,
                 details, tags, timeline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11::jsonb)
            RETURNING id, created_at, updated_at
            """,
            title,
            description,
            severity,
            status,
            source,
            kind,
            source_ip,
            host,
            json.dumps(details),
            tags,
            json.dumps(timeline),
        )
        iid = row["id"]
        genesis = "0" * 64
        chain_id = await append_chain_row(
            conn,
            iid,
            1,
            genesis,
            "created",
            {"title": title, "severity": severity, "source": source},
        )
        await conn.execute(
            "UPDATE soc_ops.security_incidents SET chain_block_id = $1 WHERE id = $2",
            chain_id,
            iid,
        )
        result = await get_incident_by_id(conn, iid)
    try:
        from mycosoft_mas.soc.security_events_stream import publish_incident_created

        await publish_incident_created(result)
    except Exception as exc:  # noqa: BLE001
        logger.debug("incident stream publish skipped: %s", exc)
    return result


async def count_recent_incidents_by_source_kind(
    source: str,
    kind: str,
    within_minutes: int = 120,
) -> int:
    """De-dupe automated incident sources (diagnostics, discovery, etc.)."""
    pool = await _pool()
    async with pool.acquire() as conn:
        n = await conn.fetchval(
            """
            SELECT COUNT(*)::int FROM soc_ops.security_incidents
            WHERE source = $1 AND kind = $2
              AND created_at > NOW() - ($3 * interval '1 minute')
            """,
            source,
            kind,
            int(within_minutes),
        )
    return int(n or 0)


async def get_incident_by_id(conn: Any, incident_id: UUID) -> Dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT id, title, description, severity, status, source, kind, source_ip, host,
               details, tags, timeline, created_at, updated_at, ack_at, resolved_at, closed_at,
               chain_block_id, assigned_to
        FROM soc_ops.security_incidents WHERE id = $1
        """,
        incident_id,
    )
    if not row:
        return {}
    return _incident_row_to_dict(row)


def _incident_row_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row["description"],
        "severity": row["severity"],
        "status": row["status"],
        "source": row["source"],
        "kind": row["kind"],
        "source_ip": row["source_ip"],
        "host": row["host"],
        "details": row["details"]
        if isinstance(row["details"], dict)
        else json.loads(row["details"] or "{}"),
        "tags": list(row["tags"] or []),
        "timeline": row["timeline"]
        if isinstance(row["timeline"], list)
        else json.loads(row["timeline"] or "[]"),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "ack_at": row["ack_at"].isoformat() if row["ack_at"] else None,
        "resolved_at": row["resolved_at"].isoformat() if row["resolved_at"] else None,
        "closed_at": row["closed_at"].isoformat() if row["closed_at"] else None,
        "chain_block_id": row["chain_block_id"],
        "assigned_to": row["assigned_to"],
    }


async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        if status and severity:
            rows = await conn.fetch(
                """
                SELECT id, title, description, severity, status, source, kind, source_ip, host,
                       details, tags, timeline, created_at, updated_at, ack_at, resolved_at, closed_at,
                       chain_block_id, assigned_to
                FROM soc_ops.security_incidents
                WHERE status = $1 AND severity = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                status,
                severity,
                limit,
                offset,
            )
        elif status:
            rows = await conn.fetch(
                """
                SELECT id, title, description, severity, status, source, kind, source_ip, host,
                       details, tags, timeline, created_at, updated_at, ack_at, resolved_at, closed_at,
                       chain_block_id, assigned_to
                FROM soc_ops.security_incidents
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                status,
                limit,
                offset,
            )
        elif severity:
            rows = await conn.fetch(
                """
                SELECT id, title, description, severity, status, source, kind, source_ip, host,
                       details, tags, timeline, created_at, updated_at, ack_at, resolved_at, closed_at,
                       chain_block_id, assigned_to
                FROM soc_ops.security_incidents
                WHERE severity = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                severity,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, title, description, severity, status, source, kind, source_ip, host,
                       details, tags, timeline, created_at, updated_at, ack_at, resolved_at, closed_at,
                       chain_block_id, assigned_to
                FROM soc_ops.security_incidents
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [_incident_row_to_dict(r) for r in rows]


async def update_incident(
    incident_id: str,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    timeline_append: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    pool = await _pool()
    uid = UUID(incident_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM soc_ops.security_incidents WHERE id = $1 FOR UPDATE", uid
        )
        if not row:
            return None
        timeline = (
            row["timeline"]
            if isinstance(row["timeline"], list)
            else json.loads(row["timeline"] or "[]")
        )
        if timeline_append:
            timeline.append(timeline_append)
        sets = ["updated_at = NOW()", "timeline = $1::jsonb"]
        args: List[Any] = [json.dumps(timeline)]
        n = 2
        if status:
            sets.append(f"status = ${n}")
            args.append(status)
            n += 1
            if status == "acknowledged":
                sets.append("ack_at = COALESCE(ack_at, NOW())")
            if status in ("resolved", "closed"):
                sets.append("resolved_at = COALESCE(resolved_at, NOW())")
            if status == "closed":
                sets.append("closed_at = COALESCE(closed_at, NOW())")
        if assigned_to is not None:
            sets.append(f"assigned_to = ${n}")
            args.append(assigned_to)
            n += 1
        args.append(uid)
        await conn.execute(
            f"UPDATE soc_ops.security_incidents SET {', '.join(sets)} WHERE id = ${n}",
            *args,
        )
        last_seq = await conn.fetchval(
            "SELECT COALESCE(MAX(sequence_number), 0) FROM soc_ops.incident_chain WHERE incident_id = $1",
            uid,
        )
        prev = await conn.fetchval(
            """
            SELECT event_hash FROM soc_ops.incident_chain
            WHERE incident_id = $1 AND sequence_number = $2
            """,
            uid,
            last_seq,
        )
        if not prev:
            prev = "0" * 64
        seq = int(last_seq) + 1
        await append_chain_row(
            conn,
            uid,
            seq,
            str(prev),
            "updated",
            {"status": status, "assigned_to": assigned_to},
        )
        result = await get_incident_by_id(conn, uid)
    patch = {k: v for k, v in {"status": status, "assigned_to": assigned_to}.items() if v is not None}
    try:
        from mycosoft_mas.soc.security_events_stream import publish_incident_updated

        await publish_incident_updated(result, patch)
    except Exception as exc:  # noqa: BLE001
        logger.debug("incident stream publish skipped: %s", exc)
    return result


async def list_chain_for_incident(incident_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    pool = await _pool()
    uid = UUID(incident_id)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, sequence_number, prev_hash, event_hash, event_type, payload, created_at
            FROM soc_ops.incident_chain
            WHERE incident_id = $1
            ORDER BY sequence_number ASC
            LIMIT $2
            """,
            uid,
            limit,
        )
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["id"]),
                "sequence_number": r["sequence_number"],
                "previous_hash": r["prev_hash"],
                "event_hash": r["event_hash"],
                "event_type": r["event_type"],
                "event_data": r["payload"]
                if isinstance(r["payload"], dict)
                else json.loads(r["payload"] or "{}"),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return out


async def upsert_device_inventory(
    *,
    mac: Optional[str],
    ip: Optional[str],
    hostname: Optional[str],
    board_type: Optional[str],
    device_id: Optional[str],
    source: str,
    classified_as: Optional[str],
    status: str,
    capabilities: Dict[str, Any],
    raw: Dict[str, Any],
) -> None:
    pool = await _pool()
    mac_norm = mac.strip().lower() if mac and mac.strip() else None
    async with pool.acquire() as conn:
        existing = None
        if mac_norm:
            existing = await conn.fetchrow(
                "SELECT id FROM soc_ops.device_inventory WHERE mac = $1",
                mac_norm,
            )
        if not existing and ip:
            existing = await conn.fetchrow(
                "SELECT id FROM soc_ops.device_inventory WHERE ip = $1::inet",
                ip,
            )
        if existing:
            await conn.execute(
                """
                UPDATE soc_ops.device_inventory SET
                    mac = COALESCE($2, mac),
                    ip = COALESCE($3::inet, ip),
                    hostname = COALESCE($4, hostname),
                    board_type = COALESCE($5, board_type),
                    device_id = COALESCE($6, device_id),
                    source = $7,
                    classified_as = COALESCE($8, classified_as),
                    status = $9,
                    capabilities = $10::jsonb,
                    raw = $11::jsonb,
                    last_seen = NOW(),
                    updated_at = NOW()
                WHERE id = $1
                """,
                existing["id"],
                mac_norm,
                ip,
                hostname,
                board_type,
                device_id,
                source,
                classified_as,
                status,
                json.dumps(capabilities),
                json.dumps(raw),
            )
        else:
            await conn.execute(
                """
                INSERT INTO soc_ops.device_inventory
                    (mac, ip, hostname, board_type, device_id, source, classified_as, status,
                     capabilities, raw, first_seen, last_seen, updated_at)
                VALUES ($1, $2::inet, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, NOW(), NOW(), NOW())
                """,
                mac_norm,
                ip,
                hostname,
                board_type,
                device_id,
                source,
                classified_as,
                status,
                json.dumps(capabilities),
                json.dumps(raw),
            )


async def list_device_inventory(limit: int = 500) -> List[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, mac, host(ip) as ip, hostname, board_type, device_id, source, classified_as,
                   status, capabilities, raw, first_seen, last_seen, updated_at
            FROM soc_ops.device_inventory
            ORDER BY last_seen DESC
            LIMIT $1
            """,
            limit,
        )
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["id"]),
                "mac": r["mac"],
                "ip": r["ip"],
                "hostname": r["hostname"],
                "board_type": r["board_type"],
                "device_id": r["device_id"],
                "source": r["source"],
                "classified_as": r["classified_as"],
                "status": r["status"],
                "capabilities": r["capabilities"]
                if isinstance(r["capabilities"], dict)
                else {},
                "raw": r["raw"] if isinstance(r["raw"], dict) else {},
                "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
                "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
        )
    return out


async def create_redteam_run(layer: int, scope: str, tool: str, params: Dict[str, Any]) -> UUID:
    pool = await _pool()
    async with pool.acquire() as conn:
        rid = await conn.fetchval(
            """
            INSERT INTO soc_ops.redteam_runs (layer, scope, tool, params, status)
            VALUES ($1, $2, $3, $4::jsonb, 'running')
            RETURNING id
            """,
            layer,
            scope,
            tool,
            json.dumps(params),
        )
        return rid


async def finish_redteam_run(
    run_id: UUID, status: str, summary: str, raw_log: Optional[str] = None
) -> None:
    pool = await _pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE soc_ops.redteam_runs
            SET status = $2, ended_at = NOW(), summary = $3, raw_log = $4
            WHERE id = $1
            """,
            run_id,
            status,
            summary,
            raw_log,
        )


async def insert_redteam_finding(
    run_id: UUID,
    severity: str,
    title: str,
    evidence: Dict[str, Any],
    control_id: Optional[str] = None,
) -> UUID:
    pool = await _pool()
    async with pool.acquire() as conn:
        fid = await conn.fetchval(
            """
            INSERT INTO soc_ops.redteam_findings (run_id, severity, control_id, title, evidence)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING id
            """,
            run_id,
            severity,
            control_id,
            title,
            json.dumps(evidence),
        )
        return fid


async def list_redteam_runs(limit: int = 30) -> List[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, layer, scope, tool, params, status, started_at, ended_at, summary
            FROM soc_ops.redteam_runs
            ORDER BY started_at DESC
            LIMIT $1
            """,
            limit,
        )
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        if d.get("params") and not isinstance(d["params"], dict):
            d["params"] = json.loads(d["params"])
        if d.get("started_at"):
            d["started_at"] = d["started_at"].isoformat()
        if d.get("ended_at"):
            d["ended_at"] = d["ended_at"].isoformat()
        out.append(d)
    return out


async def list_redteam_findings(run_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        if run_id:
            rows = await conn.fetch(
                """
                SELECT id, run_id, severity, control_id, title, evidence, status, created_at
                FROM soc_ops.redteam_findings
                WHERE run_id = $1::uuid
                ORDER BY created_at DESC
                LIMIT $2
                """,
                run_id,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, run_id, severity, control_id, title, evidence, status, created_at
                FROM soc_ops.redteam_findings
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["id"]),
                "run_id": str(r["run_id"]),
                "severity": r["severity"],
                "control_id": r["control_id"],
                "title": r["title"],
                "evidence": r["evidence"]
                if isinstance(r["evidence"], dict)
                else json.loads(r["evidence"] or "{}"),
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return out


async def upsert_compliance_control(
    control_id: str,
    framework: str,
    family: Optional[str],
    title: Optional[str],
    implementation_state: str,
    evidence_uri: Optional[str],
    state_snapshot: Dict[str, Any],
) -> None:
    pool = await _pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO soc_ops.compliance_controls
                (control_id, framework, family, title, implementation_state, evidence_uri,
                 last_verified_at, state_snapshot, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7::jsonb, NOW())
            ON CONFLICT (control_id) DO UPDATE SET
                family = COALESCE(EXCLUDED.family, soc_ops.compliance_controls.family),
                title = COALESCE(EXCLUDED.title, soc_ops.compliance_controls.title),
                implementation_state = EXCLUDED.implementation_state,
                evidence_uri = COALESCE(EXCLUDED.evidence_uri, soc_ops.compliance_controls.evidence_uri),
                last_verified_at = NOW(),
                state_snapshot = EXCLUDED.state_snapshot,
                updated_at = NOW()
            """,
            control_id,
            framework,
            family,
            title,
            implementation_state,
            evidence_uri,
            json.dumps(state_snapshot),
        )


async def list_compliance_controls() -> List[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT control_id, framework, family, title, implementation_state, evidence_uri,
                   last_verified_at, state_snapshot, updated_at
            FROM soc_ops.compliance_controls
            ORDER BY control_id
            """
        )
    out = []
    for r in rows:
        out.append(
            {
                "control_id": r["control_id"],
                "framework": r["framework"],
                "family": r["family"],
                "title": r["title"],
                "implementation_state": r["implementation_state"],
                "evidence_uri": r["evidence_uri"],
                "last_verified_at": r["last_verified_at"].isoformat()
                if r["last_verified_at"]
                else None,
                "state_snapshot": r["state_snapshot"]
                if isinstance(r["state_snapshot"], dict)
                else json.loads(r["state_snapshot"] or "{}"),
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
        )
    return out


async def insert_compliance_doc(
    doc_type: str,
    title: str,
    body_md: str,
    model_versions: Dict[str, Any],
    approved_by: Optional[str] = None,
) -> Dict[str, Any]:
    pool = await _pool()
    async with pool.acquire() as conn:
        ver = await conn.fetchval(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM soc_ops.compliance_docs WHERE doc_type = $1",
            doc_type,
        )
        row = await conn.fetchrow(
            """
            INSERT INTO soc_ops.compliance_docs (doc_type, version, title, body_md, model_versions, approved_by)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING id, doc_type, version, title, generated_at
            """,
            doc_type,
            int(ver),
            title,
            body_md,
            json.dumps(model_versions),
            approved_by,
        )
        return {
            "id": str(row["id"]),
            "doc_type": row["doc_type"],
            "version": row["version"],
            "title": row["title"],
            "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
        }


async def get_latest_compliance_doc(doc_type: str) -> Optional[Dict[str, Any]]:
    pool = await _pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, doc_type, version, title, body_md, model_versions, generated_at, approved_by
            FROM soc_ops.compliance_docs
            WHERE doc_type = $1
            ORDER BY version DESC, generated_at DESC
            LIMIT 1
            """,
            doc_type,
        )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "doc_type": row["doc_type"],
        "version": row["version"],
        "title": row["title"],
        "body_md": row["body_md"],
        "model_versions": row["model_versions"]
        if isinstance(row["model_versions"], dict)
        else json.loads(row["model_versions"] or "{}"),
        "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
        "approved_by": row["approved_by"],
    }


async def compliance_score() -> Dict[str, Any]:
    pool = await _pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
              COUNT(*)::int AS total,
              COUNT(*) FILTER (WHERE implementation_state = 'implemented')::int AS implemented,
              COUNT(*) FILTER (WHERE implementation_state = 'partial')::int AS partial
            FROM soc_ops.compliance_controls
            """
        )
    total = row["total"] or 0
    impl = row["implemented"] or 0
    pct = round(100.0 * impl / total, 1) if total else 0.0
    return {
        "total_controls": total,
        "implemented": impl,
        "partial": row["partial"] or 0,
        "implementation_percent": pct,
    }
