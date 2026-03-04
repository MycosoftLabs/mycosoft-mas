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

import os
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

import aiohttp

logger = logging.getLogger("myca.os.comms")


class Channel(str, Enum):
    DISCORD = "discord"
    SIGNAL = "signal"
    WHATSAPP = "whatsapp"
    ASANA = "asana"
    EMAIL = "email"
    SLACK = "slack"


class Urgency(str, Enum):
    LOW = "low"           # Log only, no notification
    NORMAL = "normal"     # Discord
    HIGH = "high"         # Slack + Discord
    CRITICAL = "critical" # Signal + all channels


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
    Channel.DISCORD: os.getenv("MORGAN_DISCORD_ID", ""),
    Channel.SIGNAL: os.getenv("MORGAN_SIGNAL_NUMBER", ""),
    Channel.WHATSAPP: os.getenv("MORGAN_WHATSAPP_NUMBER", ""),
    Channel.SLACK: os.getenv("MORGAN_SLACK_ID", ""),
    Channel.EMAIL: os.getenv("MORGAN_EMAIL", "morgan@mycosoft.org"),
}


class CommsHub:
    """Unified communication hub for MYCA."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        self._discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        self._signal_api = os.getenv("SIGNAL_API_URL", "http://localhost:8089")
        self._signal_number = os.getenv("SIGNAL_SENDER_NUMBER", "")
        self._slack_token = os.getenv("SLACK_BOT_TOKEN", "")
        self._asana_token = os.getenv("ASANA_PAT", "")
        self._workspace_url = os.getenv("MYCA_WORKSPACE_URL", "http://localhost:8000")
        self._message_queue: asyncio.Queue = asyncio.Queue()

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

    async def send_to_morgan(self, message: str, channel: str = "discord", urgency: Urgency = Urgency.NORMAL):
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
            await self._send_discord(response, thread_id=original_msg.get("thread_id"))
        elif source == "signal":
            await self._send_signal(sender, response)
        elif source == "whatsapp":
            await self._send_whatsapp(sender, response)
        elif source == "slack":
            await self._send_slack_dm(sender, response)
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

        # Poll workspace API (aggregated webhook inbox)
        try:
            workspace_msgs = await self._poll_workspace_inbox()
            messages.extend(workspace_msgs)
        except Exception as e:
            logger.debug(f"Workspace inbox poll: {e}")

        return messages

    # ── Channel Implementations ──────────────────────────────────

    async def _send_discord(self, message: str, mention_morgan: bool = False, thread_id: str = None):
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
        headers = {"Authorization": f"Bearer {self._slack_token}", "Content-Type": "application/json"}
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

        headers = {"Authorization": f"Bearer {self._slack_token}", "Content-Type": "application/json"}
        async with self._session.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel, "text": message},
        ) as resp:
            pass

    async def _send_email(self, to: str, subject: str, body: str):
        """Send email via workspace API (which uses Google service account)."""
        await self._send_via_workspace(to, body, "email", extra={"subject": subject})

    async def _send_via_workspace(self, recipient: str, message: str, platform: str, extra: dict = None):
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
                            messages.append({
                                "source": "signal",
                                "sender": sender,
                                "content": data_msg["message"],
                                "is_morgan": sender == MORGAN_IDS.get(Channel.SIGNAL),
                                "raw": item,
                            })
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
