"""
DocuSign API — CMMC / compliance envelope create, status, and webhook hints.

Secrets never appear in responses. JWT requires DOCUSIGN_RSA_PRIVATE_KEY_PATH.
Do not flip soc_ops to implemented from these endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from mycosoft_mas.integrations.docusign_client import DocuSignClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docusign", tags=["docusign", "compliance"])


def _client() -> DocuSignClient:
    return DocuSignClient()


class SignerIn(BaseModel):
    email: str
    name: str
    recipient_id: str = "1"
    routing_order: str = "1"
    tabs: Optional[Dict[str, Any]] = None


class DocumentIn(BaseModel):
    document_base64: str = Field(..., description="Base64 document bytes")
    name: str
    file_extension: str = "pdf"
    document_id: str = "1"


class CreateEnvelopeRequest(BaseModel):
    email_subject: str
    documents: List[DocumentIn]
    signers: List[SignerIn]
    status: str = Field(default="created", pattern="^(created|sent)$")
    email_blurb: Optional[str] = None
    pack_id: Optional[str] = Field(
        default=None,
        description="Optional CMMC pack: ma_maintenance | ps_rj_access | policy_family_batch",
    )


class CmmcEnvelopeRequest(BaseModel):
    pack_id: str = Field(..., description="ma_maintenance | ps_rj_access | policy_family_batch")
    documents: List[DocumentIn]
    signers: List[SignerIn]
    status: str = Field(default="created", pattern="^(created|sent)$")


@router.get("/health")
async def docusign_health():
    client = _client()
    try:
        return await client.health_check()
    finally:
        await client.close()


@router.get("/packs")
async def list_cmmc_packs():
    client = _client()
    return {"packs": client.list_cmmc_packs()}


@router.post("/envelopes")
async def create_envelope(body: CreateEnvelopeRequest):
    client = _client()
    try:
        documents = [
            {
                "documentBase64": d.document_base64,
                "name": d.name,
                "fileExtension": d.file_extension,
                "documentId": d.document_id,
            }
            for d in body.documents
        ]
        signers = [
            {
                "email": s.email,
                "name": s.name,
                "recipientId": s.recipient_id,
                "routingOrder": s.routing_order,
                **({"tabs": s.tabs} if s.tabs else {}),
            }
            for s in body.signers
        ]
        if body.pack_id:
            result = await client.create_cmmc_envelope(
                body.pack_id,
                documents=documents,
                signers=signers,
                status=body.status,
            )
        else:
            result = await client.create_envelope_from_document(
                email_subject=body.email_subject,
                documents=documents,
                signers=signers,
                status=body.status,
                email_blurb=body.email_blurb,
            )
        if result.get("status") == "error" and result.get("error") == "RSA key required":
            raise HTTPException(status_code=503, detail=result)
        if result.get("status") == "error":
            raise HTTPException(status_code=502, detail=result)
        return result
    finally:
        await client.close()


@router.post("/envelopes/cmmc")
async def create_cmmc_envelope(body: CmmcEnvelopeRequest):
    client = _client()
    try:
        documents = [
            {
                "documentBase64": d.document_base64,
                "name": d.name,
                "fileExtension": d.file_extension,
                "documentId": d.document_id,
            }
            for d in body.documents
        ]
        signers = [
            {
                "email": s.email,
                "name": s.name,
                "recipientId": s.recipient_id,
                "routingOrder": s.routing_order,
                **({"tabs": s.tabs} if s.tabs else {}),
            }
            for s in body.signers
        ]
        result = await client.create_cmmc_envelope(
            body.pack_id,
            documents=documents,
            signers=signers,
            status=body.status,
        )
        if result.get("status") == "error" and result.get("error") in (
            "RSA key required",
            "unknown_pack",
            "not_configured",
        ):
            code = 400 if result.get("error") == "unknown_pack" else 503
            raise HTTPException(status_code=code, detail=result)
        if result.get("status") == "error":
            raise HTTPException(status_code=502, detail=result)
        return result
    finally:
        await client.close()


@router.get("/envelopes/{envelope_id}")
async def get_envelope(envelope_id: str):
    client = _client()
    try:
        result = await client.get_envelope(envelope_id)
        if result.get("status") == "error" and result.get("error") == "RSA key required":
            raise HTTPException(status_code=503, detail=result)
        if result.get("status") == "error":
            raise HTTPException(status_code=502, detail=result)
        return result
    finally:
        await client.close()


@router.post("/webhooks/connect")
async def docusign_connect_webhook(request: Request):
    """
    DocuSign Connect receiver.

    On completed envelopes, returns evidence path hints only.
    Does NOT write soc_ops implementation_state.
    """
    try:
        payload = await request.json()
    except Exception:
        # Connect may send XML; accept raw for logging hint only
        raw = (await request.body())[:2000]
        logger.info("DocuSign webhook non-JSON payload (%s bytes)", len(raw))
        return {
            "ok": True,
            "parsed": False,
            "message": "Non-JSON Connect payload received; configure JSON format if possible.",
            "evidence_path_hint": "docs/cmmc_evidence/",
        }

    envelope_id = (
        payload.get("envelopeId")
        or payload.get("envelope_id")
        or (payload.get("data") or {}).get("envelopeId")
    )
    envelope_status = (
        payload.get("status")
        or payload.get("envelopeStatus")
        or (payload.get("data") or {}).get("envelopeSummary", {}).get("status")
        or "unknown"
    )
    pack_id = None
    custom = payload.get("customFields") or payload.get("custom_fields") or {}
    if isinstance(custom, dict):
        pack_id = custom.get("cmmc_pack_id") or custom.get("pack_id")

    client = _client()
    hint = client.evidence_hint_for_webhook(str(envelope_status), pack_id)
    logger.info(
        "DocuSign webhook envelope_id=%s status=%s completed=%s",
        envelope_id,
        envelope_status,
        hint.get("completed"),
    )
    return {
        "ok": True,
        "envelope_id": envelope_id,
        **hint,
        "soc_ops_note": "No automatic Met flip — SAO must validate signed PDF first.",
    }
