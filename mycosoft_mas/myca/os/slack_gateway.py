"""
MYCA Slack Gateway — Two-way Slack bot for real-time conversations.

Uses slack_bolt Socket Mode (no public webhook needed).
Listens for DMs and @mentions, forwards to MycaOS _handle_message(),
and sends responses back in-thread.

Requires: SLACK_BOT_TOKEN (xoxb-), SLACK_APP_TOKEN (xapp-) from api.slack.com.
Morgan must enable Socket Mode and generate the App-Level Token.

Date: 2026-03-04
"""

import os
import logging
import threading
import asyncio
from typing import Optional, Any

logger = logging.getLogger("myca.os.slack")


class SlackGateway:
    """
    Slack bot that listens for messages via Socket Mode and forwards to MycaOS.
    Runs in a background thread (SocketModeHandler is blocking).
    """

    def __init__(self, os_ref: Any):
        self._os = os_ref
        self._bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self._app_token = os.getenv("SLACK_APP_TOKEN", "")
        self._morgan_id = os.getenv("MORGAN_SLACK_ID", "")
        self._handler: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._app: Optional[Any] = None

    def _ensure_tokens(self) -> bool:
        if not self._bot_token or not self._app_token:
            logger.warning(
                "SLACK_BOT_TOKEN and SLACK_APP_TOKEN required for Slack gateway — disabled"
            )
            return False
        if not self._app_token.startswith("xapp-"):
            logger.warning(
                "SLACK_APP_TOKEN must be an App-Level Token (xapp-...) — disabled"
            )
            return False
        return True

    def start(self) -> None:
        """Start the Slack bot in a background thread."""
        if not self._ensure_tokens():
            return

        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
        except ImportError as e:
            logger.warning("slack_bolt not installed: %s", e)
            return

        app = App(token=self._bot_token)
        self._app = app

        def _dispatch_to_os(event: dict, say: Any, client: Any) -> None:
            """Forward message to MycaOS (runs async handler in main loop)."""
            user_id = event.get("user", "")
            channel_id = event.get("channel", "")
            text = (event.get("text") or "").strip()
            ts = event.get("ts", "")
            thread_ts = event.get("thread_ts") or ts

            if not text:
                return

            msg = {
                "source": "slack",
                "sender": user_id,
                "sender_id": user_id,
                "content": text,
                "is_morgan": user_id == self._morgan_id,
                "thread_id": channel_id,
                "slack_channel_id": channel_id,
                "slack_thread_ts": thread_ts,
                "slack_message_ts": ts,
                "slack_user_id": user_id,
            }

            try:
                loop = getattr(self._os, "_loop", None)
                if loop and not loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(
                        self._os._handle_message(msg), loop
                    )
                    future.result(timeout=120)
                else:
                    asyncio.run(self._os._handle_message(msg))
            except Exception as e:
                logger.error("Error handling Slack message: %s", e)
                try:
                    say(
                        text=f"Sorry, I hit an error: {type(e).__name__}. Try again in a moment.",
                        thread_ts=thread_ts,
                    )
                except Exception:
                    pass

        @app.event("app_mention")
        def handle_app_mention(body: dict, say: Any, client: Any):
            """Handle @MYCA mentions in channels."""
            event = body.get("event", {})
            if event.get("subtype") == "bot_message":
                return
            text = event.get("text", "")
            bot_id = client.auth_test().get("user_id", "")
            if bot_id:
                text = text.replace(f"<@{bot_id}>", "").strip()
            if not text:
                return
            event_copy = dict(event)
            event_copy["text"] = text
            _dispatch_to_os(event_copy, say, client)

        @app.event({"type": "message", "channel_type": "im"})
        def handle_dm(body: dict, say: Any, client: Any):
            """Handle direct messages only (channel_type im)."""
            event = body.get("event", {})
            if event.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
                return
            _dispatch_to_os(event, say, client)

        self._handler = SocketModeHandler(app, self._app_token)
        self._thread = threading.Thread(target=self._run_handler, daemon=True)
        self._thread.start()
        logger.info("Slack gateway started (Socket Mode)")

    def _run_handler(self) -> None:
        """Run the SocketModeHandler in this thread."""
        if self._handler:
            try:
                self._handler.start()
            except Exception as e:
                if not self._stop_requested:
                    logger.error("Slack handler error: %s", e)

    def stop(self) -> None:
        """Stop the Slack bot."""
        self._stop_requested = True
        if self._handler and hasattr(self._handler, "close"):
            try:
                self._handler.close()
            except Exception as e:
                logger.warning("Slack handler close: %s", e)
        self._handler = None
        self._app = None
        self._thread = None

    def send_message(
        self,
        channel_id: str,
        content: str,
        thread_ts: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a Slack channel/thread.
        Used by CommsHub when replying to Slack messages.
        """
        if not self._app:
            return False
        try:
            client = self._app.client
            kwargs: dict = {"channel": channel_id, "text": content}
            if thread_ts:
                kwargs["thread_ts"] = thread_ts
            result = client.chat_postMessage(**kwargs)
            return result.get("ok", False)
        except Exception as e:
            logger.error("Slack send_message failed: %s", e)
            return False
