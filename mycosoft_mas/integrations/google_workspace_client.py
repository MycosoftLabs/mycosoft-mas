"""
Google Workspace Client for MYCA

Provides Gmail, Drive, and Calendar access using a service account
impersonating schedule@mycosoft.org.
"""

import base64
import logging
import os
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AUTHORIZED_DOMAIN = "mycosoft.org"
SERVICE_ACCOUNT_KEY = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_KEY",
    "/opt/myca/credentials/google/service_account.json",
)
IMPERSONATE_EMAIL = os.getenv("MYCA_EMAIL", "schedule@mycosoft.org")


class GoogleWorkspaceClient:
    """Gmail, Drive, and Calendar access for MYCA via service account."""

    def __init__(
        self,
        service_account_key_path: str = SERVICE_ACCOUNT_KEY,
        impersonate_email: str = IMPERSONATE_EMAIL,
    ):
        self._key_path = service_account_key_path
        self._impersonate = impersonate_email
        self._gmail = None
        self._drive = None
        self._calendar = None

    def _get_credentials(self, scopes: List[str]):
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            self._key_path, scopes=scopes,
        )
        return creds.with_subject(self._impersonate)

    def _get_gmail(self):
        if self._gmail is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.compose",
            ])
            self._gmail = build("gmail", "v1", credentials=creds)
        return self._gmail

    def _get_drive(self):
        if self._drive is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.file",
            ])
            self._drive = build("drive", "v3", credentials=creds)
        return self._drive

    def _get_calendar(self):
        if self._calendar is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/calendar",
            ])
            self._calendar = build("calendar", "v3", credentials=creds)
        return self._calendar

    # ── Gmail ──

    async def send_email(
        self, to: str, subject: str, body: str, html: bool = False,
    ) -> Dict[str, Any]:
        mime_type = "html" if html else "plain"
        msg = MIMEText(body, mime_type)
        msg["to"] = to
        msg["from"] = self._impersonate
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = self._get_gmail().users().messages().send(
            userId="me", body={"raw": raw},
        ).execute()
        logger.info("Email sent to %s (id=%s)", to, result.get("id"))
        return result

    async def read_inbox(
        self, max_results: int = 10, query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = query or f"to:{self._impersonate}"
        results = self._get_gmail().users().messages().list(
            userId="me", maxResults=max_results, q=q,
        ).execute()
        messages = results.get("messages", [])
        return [
            self._get_gmail().users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            for m in messages
        ]

    async def get_email(self, message_id: str) -> Dict[str, Any]:
        return self._get_gmail().users().messages().get(
            userId="me", id=message_id, format="full",
        ).execute()

    async def create_draft(
        self, to: str, subject: str, body: str,
    ) -> Dict[str, Any]:
        msg = MIMEText(body)
        msg["to"] = to
        msg["from"] = self._impersonate
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = self._get_gmail().users().drafts().create(
            userId="me", body={"message": {"raw": raw}},
        ).execute()
        return draft

    # ── Drive ──

    async def list_files(
        self, folder_id: Optional[str] = None, query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = query or ""
        if folder_id:
            q = f"'{folder_id}' in parents" + (f" and {q}" if q else "")
        results = self._get_drive().files().list(
            q=q or None, pageSize=20,
            fields="files(id,name,mimeType,modifiedTime,size)",
        ).execute()
        return results.get("files", [])

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        return self._get_drive().files().get(
            fileId=file_id,
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
        ).execute()

    async def download_file(self, file_id: str, destination: str) -> str:
        from googleapiclient.http import MediaIoBaseDownload
        import io
        request = self._get_drive().files().get_media(fileId=file_id)
        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return destination

    async def upload_file(
        self, name: str, content: bytes, folder_id: Optional[str] = None,
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        from googleapiclient.http import MediaInMemoryUpload
        body: Dict[str, Any] = {"name": name, "mimeType": mime_type}
        if folder_id:
            body["parents"] = [folder_id]
        media = MediaInMemoryUpload(content, mimetype=mime_type)
        return self._get_drive().files().create(
            body=body, media_body=media, fields="id,name,webViewLink",
        ).execute()

    # ── Calendar ──

    async def list_events(
        self, time_min: str, time_max: str, calendar_id: str = "primary",
    ) -> List[Dict[str, Any]]:
        events = self._get_calendar().events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return events.get("items", [])

    async def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        return self._get_calendar().events().insert(
            calendarId=calendar_id, body=body,
        ).execute()

    # ── Security ──

    @staticmethod
    def verify_sender_domain(email: str) -> bool:
        domain = email.split("@")[-1] if "@" in email else ""
        return domain == AUTHORIZED_DOMAIN
