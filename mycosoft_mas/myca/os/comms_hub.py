"""
MYCA Communication Hub — Unified inbound/outbound messaging.

Routes messages between Morgan/staff and MYCA across all channels:
- Discord (bot + webhooks)
- Signal (signal-cli REST API on VM 191:8089)
- WhatsApp (Evolution API or browser automation)
- Asana (task comments + notifications)
- Email/Gmail (SMTP/IMAP via Google service account)
- Slack (bot + webhooks)

Morgan's preferred channels for different urgency levels:
- Casual/updates → Discord
- Tasks/projects → Asana
- Critical/urgent → Signal
- Work comms → Slack
- Formal/external → Email

Date: 2026-03-04
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from email.parser import BytesParser
from enum import Enum
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.comms")


def _env_any(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


class Channel(str, Enum):
    DISCORD = "discord"
    SIGNAL = "signal"
    WHATSAPP = "whatsapp"
    ASANA = "asana"
    EMAIL = "email"
    SLACK = "slack"


class Urgency(str, Enum):
    LOW = "low"  # Log only, no notification
    NORMAL = "normal"  # Discord
    HIGH = "high"  # Slack + Discord
    CRITICAL = "critical"  # Signal + all channels


@dataclass
class InboundMessage:
    """A message received from any channel."""

    source: Channel
    sender: str
    content: str
    is_morgan: bool = False
    thread_id: Optional[str] = None
    attachments: list = None
    raw: dict = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.raw is None:
            self.raw = {}


# Morgan's identifiers across platforms
MORGAN_IDS = {
    Channel.DISCORD: _env_any("MORGAN_DISCORD_ID"),
    Channel.SIGNAL: _env_any("MORGAN_SIGNAL_NUMBER"),
    Channel.WHATSAPP: _env_any("MORGAN_WHATSAPP_NUMBER"),
    Channel.SLACK: _env_any("MORGAN_SLACK_ID"),
    Channel.EMAIL: _env_any("MORGAN_EMAIL", default="morgan@mycosoft.org"),
}


class CommsHub:
    """Unified communication hub for MYCA."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._discord_webhook = _env_any("DISCORD_MYCA_WEBHOOK", "DISCORD_WEBHOOK_URL", default="")
        self._discord_bot_token = _env_any("MYCA_DISCORD_TOKEN", "DISCORD_BOT_TOKEN", default="")
        self._signal_api = _env_any(
            "MYCA_SIGNAL_CLI_URL", "SIGNAL_API_URL", default="http://192.168.0.191:8089"
        )
        self._signal_number = _env_any("MYCA_SIGNAL_NUMBER", "SIGNAL_SENDER_NUMBER", default="")
        self._slack_token = _env_any(
            "MYCA_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_OAUTH_TOKEN", default=""
        )
        self._asana_token = _env_any("ASANA_API_KEY", "ASANA_PAT", "MYCA_ASANA_TOKEN", default="")
        self._workspace_url = _env_any(
            "MYCA_WORKSPACE_URL", "MYCA_GATEWAY_URL", default="http://localhost:8100"
        )
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
        self._imap_port = int(os.getenv("IMAP_PORT", "993"))
        self._imap_user = os.getenv("IMAP_USER") or os.getenv("SMTP_USER", "")
        self._imap_password = os.getenv("IMAP_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
        self._asana_workspace = _env_any("ASANA_WORKSPACE_ID", default="")
        self._asana_seen_stories: set = set()

    async def initialize(self):
        """Initialize communication clients."""
        self._session = aiohttp.ClientSession()
        logger.info("CommsHub initialized")

        # Log which channels are configured
        channels = []
        if self._discord_webhook or self._discord_bot_token:
            channels.append("Discord")
        if self._signal_number:
            channels.append("Signal")
        if self._slack_token:
            channels.append("Slack")
        if self._asana_token:
            channels.append("Asana")
        channels.append("Email")  # Always available via workspace API
        logger.info(f"Active channels: {', '.join(channels)}")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Outbound ─────────────────────────────────────────────────

    async def send_to_morgan(
        self, message: str, channel: str = "discord", urgency: Urgency = Urgency.NORMAL
    ):
        """Send a message to Morgan on the specified channel."""
        if urgency == Urgency.CRITICAL:
            # Critical goes to Signal AND Discord
            await self._send_signal(MORGAN_IDS[Channel.SIGNAL], message)
            await self._send_discord(message, mention_morgan=True)
        elif channel == "signal":
            await self._send_signal(MORGAN_IDS[Channel.SIGNAL], message)
        elif channel == "slack":
            await self._send_slack_dm(MORGAN_IDS[Channel.SLACK], message)
        elif channel == "email":
            await self._send_email(MORGAN_IDS[Channel.EMAIL], "MYCA Update", message)
        else:
            await self._send_discord(message)

    async def reply(self, original_msg: dict, response: str):
        """Reply to a message on the same channel it came from."""
        source = original_msg.get("source", "discord")
        sender = original_msg.get("sender", "")

        if source == "discord":
            channel_id = original_msg.get("discord_channel_id")
            gateway = getattr(self._os, "_discord_gateway", None)
            if channel_id and gateway and gateway._client and gateway._client.is_ready():
                ok = await gateway.send_message(
                    channel_id=channel_id,
                    content=response,
                    thread_id=original_msg.get("discord_thread_id"),
                    reply_to_id=original_msg.get("discord_message_id"),
                )
                if ok:
                    return
            await self._send_discord(response, thread_id=original_msg.get("thread_id"))
        elif source == "slack":
            channel_id = original_msg.get("slack_channel_id")
            gateway = getattr(self._os, "_slack_gateway", None)
            if channel_id and gateway:
                ok = gateway.send_message(
                    channel_id=channel_id,
                    content=response,
                    thread_ts=original_msg.get("slack_thread_ts"),
                )
                if ok:
                    return
            await self._send_slack_dm(sender, response)
        elif source == "signal":
            await self._send_signal(sender, response)
        elif source == "whatsapp":
            await self._send_whatsapp(sender, response)
        elif source == "asana":
            task_gid = original_msg.get("asana_task_gid")
            if task_gid:
                await self._post_asana_comment(task_gid, response)
            else:
                logger.warning("Asana reply: no asana_task_gid in message")
        elif source == "email":
            await self._send_email(sender, "Re: " + original_msg.get("subject", ""), response)

    async def broadcast(self, message: str, channels: list = None):
        """Broadcast a message to multiple channels."""
        channels = channels or [Channel.DISCORD, Channel.SLACK]
        for ch in channels:
            try:
                if ch == Channel.DISCORD:
                    await self._send_discord(message)
                elif ch == Channel.SLACK:
                    await self._send_slack_channel(message)
                elif ch == Channel.SIGNAL:
                    await self._send_signal(MORGAN_IDS[Channel.SIGNAL], message)
            except Exception as e:
                logger.error(f"Broadcast to {ch} failed: {e}")

    async def handle_outbound(self, task: dict) -> dict:
        """Handle an outbound communication task."""
        channel = task.get("channel", "discord")
        recipient = task.get("recipient", "morgan")
        message = task.get("message", "")

        if recipient == "morgan":
            await self.send_to_morgan(message, channel=channel)
        else:
            # Send to staff member via workspace API
            await self._send_via_workspace(recipient, message, channel)

        return {"status": "completed", "summary": f"Sent to {recipient} via {channel}"}

    # ── Inbound (Polling) ────────────────────────────────────────

    async def poll_all_channels(self) -> list:
        """Poll all channels for new messages. Returns list of message dicts."""
        messages = []

        # Poll Discord (via bot or webhook listener)
        try:
            discord_msgs = await self._poll_discord()
            messages.extend(discord_msgs)
        except Exception as e:
            logger.debug(f"Discord poll: {e}")

        # Poll Signal
        try:
            signal_msgs = await self._poll_signal()
            messages.extend(signal_msgs)
        except Exception as e:
            logger.debug(f"Signal poll: {e}")

        # Poll WhatsApp
        try:
            whatsapp_msgs = await self._poll_whatsapp()
            messages.extend(whatsapp_msgs)
        except Exception as e:
            logger.debug(f"WhatsApp poll: {e}")

        # Poll workspace API (aggregated webhook inbox)
        try:
            workspace_msgs = await self._poll_workspace_inbox()
            messages.extend(workspace_msgs)
        except Exception as e:
            logger.debug(f"Workspace inbox poll: {e}")

        # Poll IMAP (schedule@mycosoft.org or SMTP_USER inbox)
        try:
            email_msgs = await self._poll_imap()
            messages.extend(email_msgs)
        except Exception as e:
            logger.debug(f"IMAP poll: {e}")

        # Poll Asana (task comments assigned to MYCA)
        try:
            asana_msgs = await self._poll_asana()
            messages.extend(asana_msgs)
        except Exception as e:
            logger.debug(f"Asana poll: {e}")

        return messages

    # ── Channel Implementations ──────────────────────────────────

    async def _send_discord(
        self, message: str, mention_morgan: bool = False, thread_id: str = None
    ):
        """Send message via Discord webhook."""
        if not self._discord_webhook:
            logger.debug("Discord webhook not configured")
            return

        if mention_morgan and MORGAN_IDS.get(Channel.DISCORD):
            message = f"<@{MORGAN_IDS[Channel.DISCORD]}> {message}"

        payload = {"content": message, "username": "MYCA"}
        if thread_id:
            payload["thread_id"] = thread_id

        url = self._discord_webhook
        if thread_id:
            url += f"?thread_id={thread_id}"

        async with self._session.post(url, json=payload) as resp:
            if resp.status not in (200, 204):
                logger.warning(f"Discord send failed: {resp.status}")

    async def _send_signal(self, recipient: str, message: str):
        """Send message via Signal CLI REST API."""
        if not self._signal_number or not recipient:
            logger.debug("Signal not configured")
            return

        payload = {
            "message": message,
            "number": self._signal_number,
            "recipients": [recipient],
        }
        try:
            async with self._session.post(
                f"{self._signal_api}/v2/send",
                json=payload,
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"Signal send failed: {resp.status}")
        except Exception as e:
            logger.error(f"Signal error: {e}")

    async def _send_whatsapp(self, recipient: str, message: str):
        """Send message via WhatsApp (Evolution API or workspace proxy)."""
        await self._send_via_workspace(recipient, message, "whatsapp")

    async def _send_slack_dm(self, user_id: str, message: str):
        """Send direct message via Slack."""
        if not self._slack_token:
            logger.debug("Slack not configured")
            return

        # Open DM channel, then post
        headers = {
            "Authorization": f"Bearer {self._slack_token}",
            "Content-Type": "application/json",
        }
        try:
            # Open conversation
            async with self._session.post(
                "https://slack.com/api/conversations.open",
                headers=headers,
                json={"users": user_id},
            ) as resp:
                data = await resp.json()
                channel_id = data.get("channel", {}).get("id")

            if channel_id:
                async with self._session.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json={"channel": channel_id, "text": message},
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Slack DM failed: {resp.status}")
        except Exception as e:
            logger.error(f"Slack error: {e}")

    async def _send_slack_channel(self, message: str, channel: str = None):
        """Send message to a Slack channel."""
        channel = channel or os.getenv("SLACK_DEFAULT_CHANNEL", "#myca-ops")
        if not self._slack_token:
            return

        headers = {
            "Authorization": f"Bearer {self._slack_token}",
            "Content-Type": "application/json",
        }
        await self._session.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel, "text": message},
        )

    async def _send_email(self, to: str, subject: str, body: str):
        """Send email via workspace API (which uses Google service account)."""
        await self._send_via_workspace(to, body, "email", extra={"subject": subject})

    async def _send_via_workspace(
        self, recipient: str, message: str, platform: str, extra: dict = None
    ):
        """Send via the MYCA workspace API."""
        payload = {
            "recipient": recipient,
            "message": message,
            "platform": platform,
        }
        if extra:
            payload.update(extra)

        try:
            async with self._session.post(
                f"{self._workspace_url}/api/workspace/send",
                json=payload,
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"Workspace send failed: {resp.status}")
        except Exception as e:
            logger.error(f"Workspace API error: {e}")

    # ── Polling Implementations ──────────────────────────────────

    async def _poll_discord(self) -> list:
        """Poll Discord for new messages (via bot API)."""
        # The workspace API aggregates webhook messages
        return []  # Handled via _poll_workspace_inbox

    async def _poll_signal(self) -> list:
        """Poll Signal for new messages."""
        messages = []
        try:
            async with self._session.get(
                f"{self._signal_api}/v1/receive/{self._signal_number}",
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data:
                        envelope = item.get("envelope", {})
                        data_msg = envelope.get("dataMessage", {})
                        if data_msg.get("message"):
                            sender = envelope.get("source", "")
                            messages.append(
                                {
                                    "source": "signal",
                                    "sender": sender,
                                    "content": data_msg["message"],
                                    "is_morgan": sender == MORGAN_IDS.get(Channel.SIGNAL),
                                    "raw": item,
                                }
                            )
        except Exception:
            pass
        return messages

    async def _poll_whatsapp(self) -> list:
        """Poll WhatsApp via Evolution API."""
        messages = []
        try:
            from mycosoft_mas.integrations.whatsapp_client import WhatsAppClient

            client = WhatsAppClient()
            records = await client.get_messages(limit=20)
            await client.close()
            for item in records:
                content = item.get("message", {}).get("conversation", "")
                sender = item.get("key", {}).get("remoteJid", "")
                if content:
                    messages.append(
                        {
                            "source": "whatsapp",
                            "sender": sender,
                            "sender_id": sender,
                            "content": content,
                            "is_morgan": sender == MORGAN_IDS.get(Channel.WHATSAPP),
                            "raw": item,
                        }
                    )
        except Exception:
            pass
        return messages

    async def _poll_workspace_inbox(self) -> list:
        """Poll the workspace API's aggregated message inbox."""
        try:
            async with self._session.get(
                f"{self._workspace_url}/api/workspace/inbox",
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("messages", [])
        except Exception:
            pass
        return []

    async def _poll_imap(self) -> list:
        """Poll IMAP inbox (schedule@mycosoft.org or SMTP_USER) for new emails."""
        if not self._imap_user or not self._imap_password:
            return []

        try:
            import aioimaplib
        except ImportError:
            logger.debug("aioimaplib not installed — IMAP polling disabled")
            return []

        messages = []
        client = None
        try:
            client = aioimaplib.IMAP4_SSL(host=self._imap_host, port=self._imap_port, timeout=30)
            await client.wait_hello_from_server()
            await client.login(self._imap_user, self._imap_password)
            await client.select("INBOX")

            # Search for UNSEEN messages
            response = await client.uid("search", None, "UNSEEN")
            if response.result != "OK" or not response.lines:
                return []

            # Parse UIDs from response (e.g. b'1 2 3' or similar)
            uid_line = response.lines[0] if response.lines else b""
            if isinstance(uid_line, bytes):
                uid_line = uid_line.decode("utf-8", errors="replace")
            uids = [u.strip() for u in uid_line.split() if u.strip().isdigit()]
            if not uids:
                return []

            for uid in uids:
                try:
                    fetch_resp = await client.uid("fetch", uid, "BODY.PEEK[]")
                    if fetch_resp.result != "OK" or len(fetch_resp.lines) < 2:
                        continue
                    raw = fetch_resp.lines[1]
                    if isinstance(raw, (list, tuple)):
                        raw = b"".join(raw) if raw else b""
                    msg_obj = BytesParser().parsebytes(raw)
                    from_addr = msg_obj.get("From", "")
                    subject = msg_obj.get("Subject", "")
                    body = ""
                    if msg_obj.is_multipart():
                        for part in msg_obj.walk():
                            ct = part.get_content_type()
                            if ct == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode("utf-8", errors="replace")
                                break
                    else:
                        payload = msg_obj.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="replace")
                    content = (subject + "\n\n" + body).strip() if subject else body.strip()
                    if not content:
                        content = "(no content)"
                    is_morgan = (
                        MORGAN_IDS.get(Channel.EMAIL, "").lower() in (from_addr or "").lower()
                    )
                    messages.append(
                        {
                            "source": "email",
                            "sender": from_addr,
                            "content": content,
                            "subject": subject,
                            "is_morgan": is_morgan,
                            "email_uid": uid,
                            "raw": {"From": from_addr, "Subject": subject},
                        }
                    )
                    # Mark as seen so we don't reprocess
                    await client.uid("store", uid, "+FLAGS", "\\Seen")
                except Exception as e:
                    logger.warning(f"IMAP fetch uid {uid} failed: {e}")
        except Exception as e:
            logger.debug(f"IMAP poll error: {e}")
        finally:
            if client:
                try:
                    await client.logout()
                except Exception:
                    pass
        return messages

    async def _poll_asana(self) -> list:
        """Poll Asana for new comments on tasks assigned to MYCA."""
        if not self._asana_token or not self._asana_workspace:
            return []

        messages = []
        headers = {
            "Authorization": f"Bearer {self._asana_token}",
            "Content-Type": "application/json",
        }
        try:
            # Get current user (MYCA) GID
            async with self._session.get(
                "https://app.asana.com/api/1.0/users/me",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return []
                me_data = await resp.json()
                me_gid = me_data.get("data", {}).get("gid", "")

            # Get tasks assigned to me in workspace
            async with self._session.get(
                "https://app.asana.com/api/1.0/tasks",
                headers=headers,
                params={
                    "workspace": self._asana_workspace,
                    "assignee": me_gid,
                    "opt_fields": "gid,name",
                },
            ) as resp:
                if resp.status != 200:
                    return []
                tasks_data = await resp.json()
                tasks = tasks_data.get("data", [])[:20]

            for task in tasks:
                task_gid = task.get("gid")
                task_name = task.get("name", "")
                try:
                    async with self._session.get(
                        f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories",
                        headers=headers,
                        params={"opt_fields": "gid,created_by,resource_subtype,text,created_at"},
                    ) as resp:
                        if resp.status != 200:
                            continue
                        stories_data = await resp.json()
                        stories = stories_data.get("data", [])
                    for s in stories:
                        if s.get("resource_subtype") != "comment_added":
                            continue
                        sgid = s.get("gid", "")
                        if sgid in self._asana_seen_stories:
                            continue
                        created_by = s.get("created_by", {})
                        created_by_gid = created_by.get("gid", "")
                        if created_by_gid == me_gid:
                            continue
                        text = (s.get("text") or "").strip()
                        if not text:
                            continue
                        self._asana_seen_stories.add(sgid)
                        creator_name = created_by.get("name", "unknown")
                        messages.append(
                            {
                                "source": "asana",
                                "sender": creator_name,
                                "content": text,
                                "is_morgan": False,
                                "thread_id": task_gid,
                                "asana_task_gid": task_gid,
                                "asana_task_name": task_name,
                                "asana_story_gid": sgid,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Asana task {task_gid} stories: {e}")
        except Exception as e:
            logger.debug(f"Asana poll error: {e}")
        return messages

    async def _post_asana_comment(self, task_gid: str, text: str) -> None:
        """Post a comment on an Asana task."""
        if not self._asana_token:
            return
        headers = {
            "Authorization": f"Bearer {self._asana_token}",
            "Content-Type": "application/json",
        }
        try:
            async with self._session.post(
                f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories",
                headers=headers,
                json={"data": {"text": text}},
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"Asana comment failed: {resp.status}")
        except Exception as e:
            logger.error(f"Asana comment error: {e}")
