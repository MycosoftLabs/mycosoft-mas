"""
DocuSign eSignature client for CMMC / compliance / MYCA.

Environment Variables (never hardcode secrets):
    DOCUSIGN_INTEGRATION_KEY: Integration key (client ID)
    DOCUSIGN_USER_ID: Impersonated user GUID (JWT Grant)
    DOCUSIGN_API_ACCOUNT_ID: API Account ID
    DOCUSIGN_BASE_URL: e.g. https://na4.docusign.net
    DOCUSIGN_AUTH_SERVER: e.g. https://account.docusign.com
    DOCUSIGN_RSA_PRIVATE_KEY_PATH: Path to RSA private key PEM (JWT Grant)
    DOCUSIGN_SECRET_KEY: Optional Auth Code secret (not used for JWT)
    DOCUSIGN_APP_NAME: App display name (metadata only)

JWT Grant is required for server-to-server envelope create. If the RSA path is
missing or unreadable, auth methods return a clear error (no fake tokens).
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Canonical CMMC signing packs (source HTML is outside repos; evidence lands under CODE/docs/cmmc_evidence/)
CMMC_ENVELOPE_PACKS: Dict[str, Dict[str, Any]] = {
    "ma_maintenance": {
        "title": "CMMC Maintenance Policy (MA.L2-3.7.1–3.7.6)",
        "controls": [
            "MA.L2-3.7.1",
            "MA.L2-3.7.2",
            "MA.L2-3.7.3",
            "MA.L2-3.7.4",
            "MA.L2-3.7.5",
            "MA.L2-3.7.6",
        ],
        "signers": ["Morgan Rockcoons (SAO)", "RJ Ricasata (CFO)"],
        "source_hint": "POLICY_MA_Maintenance.html (Downloads/cmmc_l2_policies)",
        "evidence_path_hint": "docs/cmmc_evidence/ma/3.7.1-3.7.6_maintenance_policy_signed.pdf",
    },
    "ps_rj_access": {
        "title": "RJ Access Agreement (PS.L2-3.9.2)",
        "controls": ["PS.L2-3.9.2"],
        "signers": ["RJ Ricasata (CFO)"],
        "source_hint": "RJ_Access_Agreement.html (Downloads/cmmc_l2_policies)",
        "evidence_path_hint": "docs/cmmc_evidence/ps/3.9.2_rj_access_agreement_signed.pdf",
    },
    "policy_family_batch": {
        "title": "CMMC 14-family policy SAO signature batch",
        "controls": [
            "AC",
            "AT",
            "AU",
            "CA",
            "CM",
            "IA",
            "IR",
            "MA",
            "MP",
            "PE",
            "PS",
            "RA",
            "SC",
            "SI",
        ],
        "signers": ["Morgan Rockcoons (SAO)"],
        "source_hint": "POLICY_* family HTML under Downloads/cmmc_l2_policies",
        "evidence_path_hint": "docs/cmmc_evidence/<family>/",
    },
}


class DocuSignClient:
    """Async DocuSign REST client (JWT Grant when RSA key path is set)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.integration_key = (
            self.config.get("integration_key") or os.environ.get("DOCUSIGN_INTEGRATION_KEY", "")
        ).strip()
        self.user_id = (self.config.get("user_id") or os.environ.get("DOCUSIGN_USER_ID", "")).strip()
        self.account_id = (
            self.config.get("account_id") or os.environ.get("DOCUSIGN_API_ACCOUNT_ID", "")
        ).strip()
        self.base_url = (
            self.config.get("base_url") or os.environ.get("DOCUSIGN_BASE_URL", "https://na4.docusign.net")
        ).rstrip("/")
        self.auth_server = (
            self.config.get("auth_server")
            or os.environ.get("DOCUSIGN_AUTH_SERVER", "https://account.docusign.com")
        ).rstrip("/")
        self.rsa_private_key_path = (
            self.config.get("rsa_private_key_path")
            or os.environ.get("DOCUSIGN_RSA_PRIVATE_KEY_PATH", "")
        ).strip()
        self.secret_key = (
            self.config.get("secret_key") or os.environ.get("DOCUSIGN_SECRET_KEY", "")
        ).strip()
        self.app_name = (
            self.config.get("app_name") or os.environ.get("DOCUSIGN_APP_NAME", "")
        ).strip()
        self.timeout = float(self.config.get("timeout", 30))
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._http: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        return bool(self.integration_key and self.user_id and self.account_id and self.base_url)

    def has_rsa_key(self) -> bool:
        if not self.rsa_private_key_path:
            return False
        return Path(self.rsa_private_key_path).expanduser().is_file()

    def configuration_status(self) -> Dict[str, Any]:
        """Safe status for health endpoints — no secrets."""
        return {
            "configured": self.is_configured(),
            "jwt_ready": self.is_configured() and self.has_rsa_key(),
            "rsa_key_present": self.has_rsa_key(),
            "auth_server_set": bool(self.auth_server),
            "base_url_host": self.base_url.split("//")[-1].split("/")[0] if self.base_url else "",
            "app_name_set": bool(self.app_name),
            "account_id_set": bool(self.account_id),
            "user_id_set": bool(self.user_id),
            "integration_key_set": bool(self.integration_key),
            "secret_key_set": bool(self.secret_key),
            "blocking_reason": self._blocking_reason(),
        }

    def _blocking_reason(self) -> Optional[str]:
        if not self.is_configured():
            return "Missing DOCUSIGN_INTEGRATION_KEY, DOCUSIGN_USER_ID, or DOCUSIGN_API_ACCOUNT_ID"
        if not self.has_rsa_key():
            return (
                "RSA key required for JWT Grant. Set DOCUSIGN_RSA_PRIVATE_KEY_PATH to a PEM file "
                "uploaded to the DocuSign app (Apps and Keys → RSA keypair)."
            )
        return None

    async def health_check(self) -> Dict[str, Any]:
        status = self.configuration_status()
        if not status["configured"]:
            return {"status": "not_configured", **status}
        if not status["jwt_ready"]:
            return {"status": "configured_pending_rsa", **status}
        return {"status": "ok", **status}

    def _rsa_key_required_error(self, operation: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "operation": operation,
            "error": "RSA key required",
            "message": (
                "DocuSign JWT Grant needs DOCUSIGN_RSA_PRIVATE_KEY_PATH pointing to the private "
                "key PEM registered on the DocuSign integration app. Auth Code may use "
                "DOCUSIGN_SECRET_KEY instead for interactive flows."
            ),
            "blocking_reason": self._blocking_reason(),
        }

    def _load_rsa_private_key(self) -> str:
        path = Path(self.rsa_private_key_path).expanduser()
        return path.read_text(encoding="utf-8")

    def _build_jwt_assertion(self) -> str:
        from jose import jwt

        now = int(time.time())
        claims = {
            "iss": self.integration_key,
            "sub": self.user_id,
            "aud": self.auth_server.replace("https://", "").replace("http://", ""),
            "iat": now,
            "exp": now + 3600,
            "scope": "signature impersonation",
        }
        private_key = self._load_rsa_private_key()
        return jwt.encode(claims, private_key, algorithm="RS256")

    async def get_access_token(self, force: bool = False) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "status": "error",
                "error": "not_configured",
                "message": self._blocking_reason(),
            }
        if not self.has_rsa_key():
            return self._rsa_key_required_error("get_access_token")

        if (
            not force
            and self._access_token
            and time.time() < self._token_expires_at - 60
        ):
            return {"status": "success", "token_cached": True}

        try:
            assertion = self._build_jwt_assertion()
        except Exception as exc:
            logger.warning("DocuSign JWT build failed: %s", exc)
            return {
                "status": "error",
                "error": "jwt_build_failed",
                "message": str(exc),
            }

        token_url = f"{self.auth_server}/oauth/token"
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            if resp.status_code >= 400:
                detail = resp.text
                # Consent required is common on first JWT use
                consent_hint = None
                if "consent_required" in detail.lower():
                    consent_hint = (
                        f"{self.auth_server}/oauth/auth?response_type=code"
                        f"&scope=signature%20impersonation"
                        f"&client_id=<INTEGRATION_KEY>"
                        f"&redirect_uri=https://www.docusign.com"
                    )
                return {
                    "status": "error",
                    "error": "token_exchange_failed",
                    "status_code": resp.status_code,
                    "detail": detail[:500],
                    "consent_url_template": consent_hint,
                }
            payload = resp.json()
            self._access_token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 3600))
            self._token_expires_at = time.time() + expires_in
            return {
                "status": "success",
                "token_cached": False,
                "expires_in": expires_in,
                "token_type": payload.get("token_type", "Bearer"),
            }
        except Exception as exc:
            logger.warning("DocuSign token exchange failed: %s", exc)
            return {"status": "error", "error": "token_exchange_exception", "message": str(exc)}

    async def _authed_client(self) -> httpx.AsyncClient:
        token_result = await self.get_access_token()
        if token_result.get("status") != "success" or not self._access_token:
            raise RuntimeError(token_result.get("message") or token_result.get("error") or "auth_failed")
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=f"{self.base_url}/restapi/v2.1",
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        else:
            self._http.headers["Authorization"] = f"Bearer {self._access_token}"
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
        self._http = None

    def list_cmmc_packs(self) -> List[Dict[str, Any]]:
        return [{"pack_id": k, **v} for k, v in CMMC_ENVELOPE_PACKS.items()]

    async def create_envelope_from_document(
        self,
        *,
        email_subject: str,
        documents: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        status: str = "created",
        email_blurb: Optional[str] = None,
        custom_fields: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an envelope.

        documents: [{documentBase64, name, fileExtension, documentId}]
        signers: [{email, name, recipientId, routingOrder, tabs?}]
        """
        if status != "created":
            return {
                "status": "error",
                "error": "draft_only",
                "message": "This integration creates draft envelopes only (status=created).",
            }
        if not self.has_rsa_key():
            return self._rsa_key_required_error("create_envelope_from_document")
        if not documents or not signers:
            return {
                "status": "error",
                "error": "invalid_request",
                "message": "documents and signers are required",
            }

        body: Dict[str, Any] = {
            "emailSubject": email_subject,
            "documents": documents,
            "recipients": {"signers": signers},
            "status": status,
        }
        if email_blurb:
            body["emailBlurb"] = email_blurb
        if custom_fields:
            body["customFields"] = {
                "textCustomFields": [
                    {"name": k, "value": v, "show": "false"} for k, v in custom_fields.items()
                ]
            }

        try:
            client = await self._authed_client()
            resp = await client.post(f"/accounts/{self.account_id}/envelopes", json=body)
            if resp.status_code >= 400:
                return {
                    "status": "error",
                    "error": "create_envelope_failed",
                    "status_code": resp.status_code,
                    "detail": resp.text[:800],
                }
            data = resp.json()
            return {
                "status": "success",
                "envelope_id": data.get("envelopeId"),
                "envelope_status": data.get("status"),
                "uri": data.get("uri"),
                "data": data,
            }
        except Exception as exc:
            logger.warning("DocuSign create_envelope failed: %s", exc)
            return {"status": "error", "error": "create_envelope_exception", "message": str(exc)}

    async def create_cmmc_envelope(
        self,
        pack_id: str,
        *,
        documents: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        status: str = "created",
    ) -> Dict[str, Any]:
        """
        Create a CMMC pack envelope. Default status=created (draft) so operators
        review before send. Does not flip soc_ops — completed PDFs must land first.
        """
        pack = CMMC_ENVELOPE_PACKS.get(pack_id)
        if not pack:
            return {
                "status": "error",
                "error": "unknown_pack",
                "message": f"Unknown pack_id={pack_id}",
                "known_packs": list(CMMC_ENVELOPE_PACKS.keys()),
            }
        result = await self.create_envelope_from_document(
            email_subject=pack["title"],
            documents=documents,
            signers=signers,
            status=status,
            email_blurb=(
                "Mycosoft CMMC signature package. Do not paste CUI into commercial AI. "
                "Completed PDF evidence path hint: " + pack["evidence_path_hint"]
            ),
            custom_fields={
                "cmmc_pack_id": pack_id,
                "evidence_path_hint": pack["evidence_path_hint"],
                "controls": ",".join(pack["controls"]),
            },
        )
        if result.get("status") == "success":
            result["pack"] = {"pack_id": pack_id, **pack}
            result["soc_ops_note"] = (
                "Do NOT set soc_ops.compliance_controls to implemented until signed PDF "
                "exists at evidence_path_hint (or PreVeil) and SAO validates."
            )
        return result

    async def get_envelope(self, envelope_id: str) -> Dict[str, Any]:
        if not self.has_rsa_key():
            return self._rsa_key_required_error("get_envelope")
        if not envelope_id:
            return {"status": "error", "error": "missing_envelope_id"}
        try:
            client = await self._authed_client()
            resp = await client.get(f"/accounts/{self.account_id}/envelopes/{envelope_id}")
            if resp.status_code >= 400:
                return {
                    "status": "error",
                    "error": "get_envelope_failed",
                    "status_code": resp.status_code,
                    "detail": resp.text[:500],
                }
            data = resp.json()
            return {
                "status": "success",
                "envelope_id": data.get("envelopeId", envelope_id),
                "envelope_status": data.get("status"),
                "data": data,
            }
        except Exception as exc:
            logger.warning("DocuSign get_envelope failed: %s", exc)
            return {"status": "error", "error": "get_envelope_exception", "message": str(exc)}

    def evidence_hint_for_webhook(self, envelope_status: str, pack_id: Optional[str] = None) -> Dict[str, Any]:
        """Map completed envelope to evidence landing path (no soc_ops flip)."""
        pack = CMMC_ENVELOPE_PACKS.get(pack_id or "")
        return {
            "envelope_status": envelope_status,
            "completed": str(envelope_status).lower() == "completed",
            "evidence_path_hint": (pack or {}).get(
                "evidence_path_hint", "docs/cmmc_evidence/"
            ),
            "next_steps": [
                "Download signed PDF from DocuSign",
                "If CUI: store authoritative copy in PreVeil only",
                "Place non-CUI attestation/pointer under docs/cmmc_evidence/",
                "SAO validates before any soc_ops implementation_state flip",
            ],
        }
