"""
Google Workspace Client for MYCA

Provides Gmail, Drive, Calendar, and Docs access using a service account
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
SERVICE_ACCOUNT_KEY = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_KEY",
    os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "/opt/myca/credentials/google/service_account.json"),
)
IMPERSONATE_EMAIL = os.environ.get("MYCA_EMAIL", "schedule@mycosoft.org")


class GoogleWorkspaceClient:
    """Gmail, Drive, Calendar, and Docs access for MYCA via service account."""

    def __init__(
        self,
        service_account_key_path: Optional[str] = None,
        impersonate_email: Optional[str] = None,
    ):
        self._key_path = service_account_key_path or SERVICE_ACCOUNT_KEY
        self._impersonate = impersonate_email or IMPERSONATE_EMAIL
        self._gmail = None
        self._drive = None
        self._calendar = None
        self._docs = None

    def _get_credentials(self, scopes: List[str]):
        from google.oauth2 import service_account
        path = self._key_path
        if path.startswith("{") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
            import json
            creds_dict = json.loads(path) if path.startswith("{") else json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds = service_account.Credentials.from_service_account_file(path, scopes=scopes)
        return creds.with_subject(self._impersonate)

    def _get_gmail(self):
        if self._gmail is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.compose",
                "https://www.googleapis.com/auth/gmail.modify",
            ])
            self._gmail = build("gmail", "v1", credentials=creds)
        return self._gmail

    def _get_drive(self):
        if self._drive is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/drive",
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
                "https://www.googleapis.com/auth/calendar.readonly",
            ])
            self._calendar = build("calendar", "v3", credentials=creds)
        return self._calendar

    def _get_docs(self):
        if self._docs is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials([
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/drive.file",
            ])
            self._docs = build("docs", "v1", credentials=creds)
        return self._docs

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

    async def search_emails(
        self, query: str, max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search emails using Gmail query syntax (from:, to:, subject:, after:, before:, etc.)."""
        results = self._get_gmail().users().messages().list(
            userId="me", maxResults=max_results, q=query,
        ).execute()
        messages = results.get("messages", [])
        return [
            self._get_gmail().users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date", "To"],
            ).execute()
            for m in messages
        ]

    async def get_email(self, message_id: str) -> Dict[str, Any]:
        return self._get_gmail().users().messages().get(
            userId="me", id=message_id, format="full",
        ).execute()

    async def add_label(self, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
        return self._get_gmail().users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": label_ids},
        ).execute()

    async def archive_email(self, message_id: str) -> Dict[str, Any]:
        return self._get_gmail().users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]},
        ).execute()

    async def trash_email(self, message_id: str) -> Dict[str, Any]:
        return self._get_gmail().users().messages().trash(userId="me", id=message_id).execute()

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

    async def share_file(
        self, file_id: str, email: str, role: str = "reader",
    ) -> Dict[str, Any]:
        """Share a file with a user. role: reader, writer, commenter."""
        perm = {"type": "user", "role": role, "emailAddress": email}
        return self._get_drive().permissions().create(
            fileId=file_id, body=perm, sendNotificationEmail=True,
        ).execute()

    async def share_file_link(
        self, file_id: str, role: str = "reader",
    ) -> Dict[str, Any]:
        """Create a shareable link. role: reader, writer, commenter."""
        perm = {"type": "anyone", "role": role}
        return self._get_drive().permissions().create(
            fileId=file_id, body=perm,
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
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        if description:
            body["description"] = description
        return self._get_calendar().events().insert(
            calendarId=calendar_id, body=body,
        ).execute()

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if summary is not None:
            body["summary"] = summary
        if start is not None:
            body["start"] = {"dateTime": start}
        if end is not None:
            body["end"] = {"dateTime": end}
        if attendees is not None:
            body["attendees"] = [{"email": e} for e in attendees]
        if description is not None:
            body["description"] = description
        return self._get_calendar().events().patch(
            calendarId=calendar_id, eventId=event_id, body=body,
        ).execute()

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        self._get_calendar().events().delete(
            calendarId=calendar_id, eventId=event_id,
        ).execute()

    async def get_free_busy(
        self, time_min: str, time_max: str, calendar_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get availability (free/busy) for calendars."""
        body: Dict[str, Any] = {
            "timeMin": time_min,
            "timeMax": time_max,
        }
        if calendar_ids:
            body["items"] = [{"id": cid} for cid in calendar_ids]
        else:
            body["items"] = [{"id": "primary"}]
        return self._get_calendar().freebusy().query(body=body).execute()

    # ── Google Docs ──

    async def create_doc(self, title: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Doc via Drive API."""
        body: Dict[str, Any] = {
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
        }
        if folder_id:
            body["parents"] = [folder_id]
        return self._get_drive().files().create(
            body=body, fields="id,name,webViewLink",
        ).execute()

    async def get_doc(self, document_id: str) -> Dict[str, Any]:
        return self._get_docs().documents().get(documentId=document_id).execute()

    async def append_text_to_doc(self, document_id: str, text: str) -> Dict[str, Any]:
        """Append text to the end of a Google Doc."""
        doc = self._get_docs().documents().get(documentId=document_id).execute()
        end_index = doc.get("body", {}).get("content", [{}])[-1].get("endIndex", 1)
        requests = [
            {
                "insertText": {
                    "location": {"index": end_index - 1},
                    "text": text,
                }
            }
        ]
        return self._get_docs().documents().batchUpdate(
            documentId=document_id, body={"requests": requests},
        ).execute()

    async def replace_text_in_doc(
        self, document_id: str, find: str, replace: str,
    ) -> Dict[str, Any]:
        """Replace all occurrences of find with replace in a Google Doc."""
        requests = [
            {"replaceAllText": {"containsText": {"text": find}, "replaceText": replace}}
        ]
        return self._get_docs().documents().batchUpdate(
            documentId=document_id, body={"requests": requests},
        ).execute()

    # ── Health ──

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Google Workspace APIs."""
        try:
            self._get_gmail().users().getProfile(userId="me").execute()
            return {"status": "healthy", "gmail": True, "drive": True, "calendar": True, "docs": True}
        except Exception as e:
            logger.warning("Google Workspace health check failed: %s", e)
            return {"status": "unhealthy", "error": str(e)}

    # ── Security ──

    @staticmethod
    def verify_sender_domain(email: str) -> bool:
        domain = email.split("@")[-1] if "@" in email else ""
        return domain == AUTHORIZED_DOMAIN
