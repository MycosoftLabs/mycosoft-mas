"""
MYCA Discord Gateway — Two-way Discord bot for real-time conversations.

Listens for DMs and @mentions, forwards to MycaOS _handle_message(),
and sends responses back via the bot (not just webhook).

Requires: DISCORD_BOT_TOKEN, Message Content Intent enabled in Discord Developer Portal.

Date: 2026-03-04
"""

import os
import asyncio
import logging
from typing import Optional, Any

logger = logging.getLogger("myca.os.discord")


class DiscordGateway:
    """
    Discord bot that listens for messages and forwards them to MycaOS.
    Runs as a concurrent task inside the MycaOS event loop.
    """

    def __init__(self, os_ref: Any):
        self._os = os_ref
        self._token = os.getenv("DISCORD_BOT_TOKEN", "")
        self._morgan_id = os.getenv("MORGAN_DISCORD_ID", "")
        self._client = None
        self._ready = asyncio.Event()

    def _ensure_token(self) -> bool:
        if not self._token:
            logger.warning("DISCORD_BOT_TOKEN not set — Discord gateway disabled")
            return False
        return True

    async def start(self) -> None:
        """Start the Discord bot. Runs until shutdown."""
        if not self._ensure_token():
            return

        try:
            import discord
        except ImportError as e:
            logger.warning("discord.py not installed: %s", e)
            return

        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message text
        intents.messages = True
        intents.dm_messages = True
        intents.guild_messages = True

        bot = discord.Client(intents=intents)

        @bot.event
        async def on_ready():
            logger.info("Discord bot connected as %s", bot.user)
            self._ready.set()

        @bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return

            # Only handle DMs or @mentions
            is_dm = message.guild is None
            is_mention = (
                message.guild is not None
                and bot.user in message.mentions
            )
            if not is_dm and not is_mention:
                return

            content = message.content
            if is_mention:
                # Strip the @MYCA mention from content
                for u in message.mentions:
                    content = content.replace(f"<@{u.id}>", "").strip()

            if not content:
                return

            msg = {
                "source": "discord",
                "sender": str(message.author),
                "sender_id": str(message.author.id),
                "content": content,
                "is_morgan": str(message.author.id) == self._morgan_id,
                "thread_id": str(message.channel.id) if message.channel else None,
                "discord_channel_id": message.channel.id if message.channel else None,
                "discord_message_id": message.id,
                "discord_reference": message.reference,
            }
            if message.channel and hasattr(message.channel, "parent_id") and message.channel.parent_id:
                msg["discord_thread_id"] = message.channel.id

            try:
                await self._os._handle_message(msg)
            except Exception as e:
                logger.error("Error handling Discord message: %s", e)
                try:
                    await message.channel.send(
                        f"Sorry, I hit an error: {type(e).__name__}. Try again in a moment."
                    )
                except Exception:
                    pass

        self._client = bot
        try:
            await bot.start(self._token)
        except Exception as e:
            logger.error("Discord bot error: %s", e)
        finally:
            self._client = None

    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._client:
            await self._client.close()
            self._client = None

    async def send_message(
        self,
        channel_id: int,
        content: str,
        thread_id: Optional[int] = None,
        reply_to_id: Optional[int] = None,
    ) -> bool:
        """
        Send a message to a Discord channel/thread via the bot.
        Used by CommsHub when replying to Discord messages.
        """
        if not self._client or not self._client.is_ready():
            return False
        try:
            import discord
            channel = self._client.get_channel(channel_id)
            if not channel:
                channel = await self._client.fetch_channel(channel_id)
            if not channel:
                logger.warning("Discord channel %s not found", channel_id)
                return False

            kwargs = {}
            if reply_to_id:
                kwargs["reference"] = discord.MessageReference(
                    channel_id=channel_id,
                    message_id=reply_to_id,
                )
            msg = await channel.send(content, **kwargs)
            return msg is not None
        except Exception as e:
            logger.error("Discord send_message failed: %s", e)
            return False
