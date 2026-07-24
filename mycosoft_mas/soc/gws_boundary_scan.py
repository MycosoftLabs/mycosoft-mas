"""Google Workspace CUI-boundary scanner with metadata-only handling.

Google Workspace is outside the CUI boundary. This worker detects marking
tokens in Drive metadata and reduces every finding to an approved location
record before persistence, notification, or API exposure.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx

logger = logging.getLogger(__name__)

DRIVE_METADATA_SCOPE = "https://www.googleapis.com/auth/drive.metadata.readonly"
MARKING_TOKENS = (
    "CONTROLLED UNCLASSIFIED",
    "SP-CTI",
    "SP-EXPT",
    "SP-PROPIN",
    "CUI//",
    "EXPORT CONTROLLED",
    "ITAR",
    "CUI",
)
SCANNED_SCOPE = (
    "Google Drive metadata (names, owners, identifiers, and modification timestamps only)"
)
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _match_marking_token(value: str) -> str | None:
    normalized = value.upper()
    return next((token for token in MARKING_TOKENS if token in normalized), None)


def sanitize_workspace_hit(
    file_metadata: dict[str, Any],
    *,
    marking_token: str,
    detected_at: str,
) -> dict[str, str]:
    """Return the only fields permitted beyond the scanner boundary."""
    owners = file_metadata.get("owners")
    first_owner = owners[0] if isinstance(owners, list) and owners else {}
    owner = first_owner.get("emailAddress") if isinstance(first_owner, dict) else None

    return {
        "source": "google_drive",
        "container": str(file_metadata.get("driveId") or "my-drive"),
        "itemId": str(file_metadata.get("id") or ""),
        "owner": str(owner or "unknown"),
        "markingToken": marking_token,
        "detectedAt": detected_at,
    }


class BoundaryScanService:
    """Coordinates credential checks, Drive metadata scanning, and SOC escalation."""

    def configuration_status(self) -> dict[str, Any]:
        has_admin = bool((os.getenv("GOOGLE_WORKSPACE_ADMIN_EMAIL") or "").strip())
        has_service_account = bool((os.getenv("GOOGLE_WORKSPACE_SA_KEY") or "").strip())
        has_reports_token = bool((os.getenv("GOOGLE_WORKSPACE_REPORTS_TOKEN") or "").strip())
        configured = has_admin and has_service_account

        if configured:
            return {
                "configured": True,
                "status": "configured-scan-pending",
                "guidance": "Service-account credentials are configured; awaiting a verified metadata-only scan.",
            }
        if has_reports_token:
            return {
                "configured": True,
                "status": "configured-scan-pending",
                "guidance": (
                    "Reports-token credentials are present, but Drive metadata scanning requires "
                    "GOOGLE_WORKSPACE_ADMIN_EMAIL and GOOGLE_WORKSPACE_SA_KEY."
                ),
            }
        return {
            "configured": False,
            "status": "not-configured",
            "guidance": (
                "Set GOOGLE_WORKSPACE_ADMIN_EMAIL and GOOGLE_WORKSPACE_SA_KEY after Morgan "
                "completes Google Admin domain-wide delegation. No scan has run."
            ),
        }

    async def run_once(self) -> dict[str, Any]:
        configuration = self.configuration_status()
        if not self._has_service_account_configuration():
            return {
                **configuration,
                "last_run": None,
                "scanned_scope": list(SCANNED_SCOPE),
                "hit_count": 0,
                "hits": [],
            }

        started_at = _utc_now()
        try:
            hits = await self._scan_drive_metadata()
        except Exception as exc:  # noqa: BLE001
            error_code = self._safe_error_code(exc)
            logger.warning("Google Workspace boundary scan failed: %s", error_code)
            await self._persist_run(
                status="error",
                started_at=started_at,
                completed_at=_utc_now(),
                hits=[],
                error_code=error_code,
                notification_status="not-required",
            )
            return {
                "configured": True,
                "status": "error",
                "guidance": "The scan failed closed. Resolve the server-side credential or API configuration.",
                "last_run": started_at,
                "scanned_scope": list(SCANNED_SCOPE),
                "hit_count": 0,
                "hits": [],
            }

        completed_at = _utc_now()
        notification_status = "not-required"
        if hits:
            notification_status = await self._escalate_hits(hits, completed_at)
        status = "hits" if hits else "clean"
        await self._persist_run(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            hits=hits,
            error_code=None,
            notification_status=notification_status,
        )
        return {
            "configured": True,
            "status": status,
            "guidance": (
                "Suspected spillage detected. Containment and SAO notification were initiated."
                if hits
                else "Verified metadata-only Drive scan completed with no marking-token matches."
            ),
            "last_run": completed_at,
            "scanned_scope": list(SCANNED_SCOPE),
            "hit_count": len(hits),
            "hits": hits,
        }

    def _has_service_account_configuration(self) -> bool:
        return bool(
            (os.getenv("GOOGLE_WORKSPACE_ADMIN_EMAIL") or "").strip()
            and (os.getenv("GOOGLE_WORKSPACE_SA_KEY") or "").strip()
        )

    async def _scan_drive_metadata(self) -> list[dict[str, str]]:
        token = await self._get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        params: dict[str, Any] = {
            "q": "trashed = false",
            "pageSize": 100,
            "fields": "nextPageToken,files(id,name,owners(emailAddress),modifiedTime,driveId)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        hits: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                response = await client.get(DRIVE_FILES_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                for file_metadata in self._files_from_response(data):
                    name = file_metadata.get("name")
                    if not isinstance(name, str):
                        continue
                    marking_token = _match_marking_token(name)
                    if marking_token:
                        hits.append(
                            sanitize_workspace_hit(
                                file_metadata,
                                marking_token=marking_token,
                                detected_at=_utc_now(),
                            )
                        )
                next_page = data.get("nextPageToken")
                if not isinstance(next_page, str) or not next_page:
                    break
                params["pageToken"] = next_page
        return hits

    @staticmethod
    def _files_from_response(data: Any) -> Iterable[dict[str, Any]]:
        if not isinstance(data, dict):
            return ()
        files = data.get("files")
        if not isinstance(files, list):
            return ()
        return (item for item in files if isinstance(item, dict))

    async def _get_service_account_token(self) -> str:
        key_data = self._load_service_account_key()
        try:
            from jose import jwt
        except ImportError as exc:
            raise RuntimeError("python-jose dependency is unavailable") from exc

        token_uri = str(key_data.get("token_uri") or "https://oauth2.googleapis.com/token")
        client_email = str(key_data.get("client_email") or "")
        private_key = str(key_data.get("private_key") or "")
        if not client_email or not private_key:
            raise RuntimeError("service account key is missing signing fields")
        issued_at = int(time.time())
        assertion = jwt.encode(
            {
                "iss": client_email,
                "sub": os.environ["GOOGLE_WORKSPACE_ADMIN_EMAIL"].strip(),
                "aud": token_uri,
                "scope": DRIVE_METADATA_SCOPE,
                "iat": issued_at,
                "exp": issued_at + 3600,
            },
            private_key,
            algorithm="RS256",
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
            response.raise_for_status()
            response_data = response.json()
        token = response_data.get("access_token") if isinstance(response_data, dict) else None
        if not isinstance(token, str) or not token:
            raise RuntimeError("service account did not return an access token")
        return token

    @staticmethod
    def _load_service_account_key() -> dict[str, Any]:
        raw_value = (os.getenv("GOOGLE_WORKSPACE_SA_KEY") or "").strip()
        if not raw_value:
            raise RuntimeError("service account key is unavailable")

        key_path = Path(raw_value)
        try:
            raw_json = key_path.read_text(encoding="utf-8") if key_path.is_absolute() else ""
        except OSError as exc:
            raise RuntimeError("service account key path is unreadable") from exc

        if not raw_json:
            try:
                raw_json = base64.b64decode(raw_value, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as exc:
                raise RuntimeError("service account key must be base64 JSON or an absolute path") from exc
        try:
            value = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("service account key JSON is invalid") from exc
        if not isinstance(value, dict):
            raise RuntimeError("service account key JSON must be an object")
        return value

    async def _escalate_hits(self, hits: list[dict[str, str]], detected_at: str) -> str:
        notification_status = "sent"
        try:
            from mycosoft_mas.soc import repository as soc_repo

            recent = await soc_repo.count_recent_incidents_by_source_kind(
                "gws_boundary_scan",
                "workspace_cui_marking",
                within_minutes=60,
            )
            if recent == 0:
                await soc_repo.create_incident(
                    title="Suspected Google Workspace CUI-boundary spillage",
                    description=(
                        "A Workspace metadata marking match was detected. Contain the item and "
                        "notify the SAO within one hour. This incident stores location metadata only."
                    ),
                    severity="high",
                    status="investigating",
                    source="gws_boundary_scan",
                    kind="workspace_cui_marking",
                    details={"hits": hits, "detected_at": detected_at},
                    tags=["auto", "cui-boundary", "ir.l2-3.6"],
                    timeline=[
                        {
                            "timestamp": detected_at,
                            "action": "suspected_spillage_detected",
                            "actor": "gws_boundary_scan",
                            "details": "Location-only metadata captured; content was not retained.",
                        }
                    ],
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unable to create GWS boundary incident: %s", self._safe_error_code(exc))

        try:
            from mycosoft_mas.services.admin_notifications import notify_morgan

            result = await notify_morgan(
                title="Suspected Google Workspace CUI-boundary spillage",
                message=(
                    "A metadata-only marking match was detected outside PreVeil. "
                    "Contain the item and review the linked SOC incident within one hour."
                ),
                type="error",
                agent="GoogleWorkspaceBoundaryScan",
                priority="critical",
                data={"hits": hits, "detected_at": detected_at},
                requires_action=True,
            )
            if result.get("status") != "sent":
                notification_status = "failed"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unable to notify SAO of boundary hit: %s", self._safe_error_code(exc))
            notification_status = "failed"
        return notification_status

    async def _persist_run(
        self,
        *,
        status: str,
        started_at: str,
        completed_at: str,
        hits: list[dict[str, str]],
        error_code: str | None,
        notification_status: str,
    ) -> None:
        try:
            from mycosoft_mas.soc import repository as soc_repo

            await soc_repo.create_gws_boundary_scan_run(
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                scanned_scope=list(SCANNED_SCOPE),
                hits=hits,
                error_code=error_code,
                notification_status=notification_status,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unable to persist GWS boundary scan state: %s", self._safe_error_code(exc))

    @staticmethod
    def _safe_error_code(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"http_{exc.response.status_code}"
        if isinstance(exc, httpx.HTTPError):
            return "http_error"
        if isinstance(exc, RuntimeError):
            return "configuration_error"
        return "scan_error"


async def get_boundary_status() -> dict[str, Any]:
    """Return persisted status when available, otherwise an honest configuration state."""
    service = BoundaryScanService()
    configuration = service.configuration_status()
    try:
        from mycosoft_mas.soc import repository as soc_repo

        latest = await soc_repo.get_latest_gws_boundary_scan_run()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to read GWS boundary scan state: %s", service._safe_error_code(exc))
        latest = None
    if latest:
        return {**configuration, **latest}
    return {
        **configuration,
        "last_run": None,
        "scanned_scope": list(SCANNED_SCOPE),
        "hit_count": 0,
        "hits": [],
    }
