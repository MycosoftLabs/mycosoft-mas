"""
MYCA OS Core — The autonomous employee daemon.

This is the main loop that makes MYCA a living, breathing employee.
It runs 24/7 on VM 191, processing messages, executing tasks, making decisions,
and continuously learning and improving.

Unlike a chatbot that waits for prompts, MYCA OS is proactive:
- Checks messages across all channels every few seconds
- Processes her task queue autonomously
- Makes executive decisions as COO/Co-CEO/Co-CTO
- Runs reflection and intention cycles
- Monitors all systems and self-heals
- Uses her tools (Claude Code, Cursor, browser, n8n) independently

Date: 2026-03-04
"""

import asyncio
import json
import os
import signal
import socket
import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger("myca.os")


class MycaState(str, Enum):
    """MYCA's operational states."""
    BOOTING = "booting"          # Starting up, loading systems
    AWAKE = "awake"              # Normal operation
    FOCUSED = "focused"          # Deep work on a specific task
    MEETING = "meeting"          # In a conversation with Morgan or staff
    MONITORING = "monitoring"    # Night mode, low activity
    REFLECTING = "reflecting"    # Running reflection/learning cycle
    SHUTTING_DOWN = "shutting_down"


@dataclass
class MycaContext:
    """Runtime context for the MYCA OS."""
    state: MycaState = MycaState.BOOTING
    boot_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_task: Optional[str] = None
    tasks_completed_today: int = 0
    messages_processed_today: int = 0
    decisions_made_today: int = 0
    last_morgan_contact: Optional[datetime] = None
    last_checkin_sent: Optional[datetime] = None
    last_reflection: Optional[datetime] = None
    last_intention_cycle: Optional[datetime] = None
    cycle_count: int = 0
    errors_today: int = 0


class MycaOS:
    """
    MYCA Operating System — The autonomous employee daemon.

    This is the persistent process that runs on VM 191 and makes MYCA
    a real, autonomous employee. It integrates:

    - CommsHub: All communication channels (Discord, Signal, WhatsApp, Asana, Email)
    - ToolOrchestrator: All tools MYCA can use (Claude Code, Cursor, browser, n8n, Git)
    - ExecutiveSystem: Decision-making as COO/Co-CEO/Co-CTO
    - MAS Bridge: Connection to the 158+ agent orchestrator on VM 188
    - MINDEX Bridge: Connection to all databases on VM 189
    - Consciousness: Integration with MYCA's consciousness system
    """

    # Cycle intervals (seconds)
    MESSAGE_POLL_INTERVAL = 5        # Check messages every 5s
    HEARTBEAT_INTERVAL = 30          # System health every 30s
    MORGAN_CHECKIN_INTERVAL = 1800   # Proactive check-in to Morgan every 30 min
    TASK_PROCESS_INTERVAL = 10       # Process task queue every 10s
    INTENTION_INTERVAL = 900         # Review goals every 15min
    REFLECTION_INTERVAL = 3600       # Learn from outcomes every 1hr
    DAILY_RHYTHM_CHECK = 60          # Check daily schedule every 1min

    def __init__(self):
        self.ctx = MycaContext()
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Lazy-loaded subsystems
        self._comms: Optional["CommsHub"] = None
        self._tools: Optional["ToolOrchestrator"] = None
        self._executive: Optional["ExecutiveSystem"] = None
        self._mas_bridge: Optional["MASBridge"] = None
        self._mindex_bridge: Optional["MINDEXBridge"] = None
        self._crep_bridge: Optional["CREPBridge"] = None
        self._earth2_bridge: Optional["Earth2Bridge"] = None
        self._mycobrain_bridge: Optional["MycoBrainBridge"] = None
        self._openwork_bridge: Optional["OpenWorkBridge"] = None
        self._browser_cdp: Optional["BrowserCDP"] = None
        self._n8n_bridge: Optional["N8NBridge"] = None
        self._scheduler: Optional["Scheduler"] = None
        self._file_manager: Optional["FileManager"] = None
        self._discord_gateway: Optional["DiscordGateway"] = None
        self._slack_gateway: Optional["SlackGateway"] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Subsystem accessors (lazy-load) ──────────────────────────

    @property
    def comms(self) -> "CommsHub":
        if self._comms is None:
            from mycosoft_mas.myca.os.comms_hub import CommsHub
            self._comms = CommsHub(self)
        return self._comms

    @property
    def tools(self) -> "ToolOrchestrator":
        if self._tools is None:
            from mycosoft_mas.myca.os.tool_orchestrator import ToolOrchestrator
            self._tools = ToolOrchestrator(self)
        return self._tools

    @property
    def executive(self) -> "ExecutiveSystem":
        if self._executive is None:
            from mycosoft_mas.myca.os.executive import ExecutiveSystem
            self._executive = ExecutiveSystem(self)
        return self._executive

    @property
    def mas_bridge(self) -> "MASBridge":
        if self._mas_bridge is None:
            from mycosoft_mas.myca.os.mas_bridge import MASBridge
            self._mas_bridge = MASBridge(self)
        return self._mas_bridge

    @property
    def mindex_bridge(self) -> "MINDEXBridge":
        if self._mindex_bridge is None:
            from mycosoft_mas.myca.os.mindex_bridge import MINDEXBridge
            self._mindex_bridge = MINDEXBridge(self)
        return self._mindex_bridge

    @property
    def crep_bridge(self) -> "CREPBridge":
        if self._crep_bridge is None:
            from mycosoft_mas.myca.os.crep_bridge import CREPBridge
            self._crep_bridge = CREPBridge(self)
        return self._crep_bridge

    @property
    def earth2_bridge(self) -> "Earth2Bridge":
        if self._earth2_bridge is None:
            from mycosoft_mas.myca.os.earth2_bridge import Earth2Bridge
            self._earth2_bridge = Earth2Bridge(self)
        return self._earth2_bridge

    @property
    def mycobrain_bridge(self) -> "MycoBrainBridge":
        if self._mycobrain_bridge is None:
            from mycosoft_mas.myca.os.mycobrain_bridge import MycoBrainBridge
            self._mycobrain_bridge = MycoBrainBridge(self)
        return self._mycobrain_bridge

    @property
    def openwork_bridge(self) -> "OpenWorkBridge":
        if self._openwork_bridge is None:
            from mycosoft_mas.myca.os.openwork_bridge import OpenWorkBridge
            self._openwork_bridge = OpenWorkBridge(self)
        return self._openwork_bridge

    @property
    def browser_cdp(self) -> "BrowserCDP":
        if self._browser_cdp is None:
            from mycosoft_mas.myca.os.browser_cdp import BrowserCDP
            self._browser_cdp = BrowserCDP(self)
        return self._browser_cdp

    @property
    def n8n_bridge(self) -> "N8NBridge":
        if self._n8n_bridge is None:
            from mycosoft_mas.myca.os.n8n_bridge import N8NBridge
            self._n8n_bridge = N8NBridge(self)
        return self._n8n_bridge

    @property
    def scheduler(self) -> "Scheduler":
        if self._scheduler is None:
            from mycosoft_mas.myca.os.scheduler import Scheduler
            self._scheduler = Scheduler(self)
        return self._scheduler

    @property
    def file_manager(self) -> "FileManager":
        if self._file_manager is None:
            from mycosoft_mas.myca.os.file_manager import FileManager
            self._file_manager = FileManager(self)
        return self._file_manager

    # ── Lifecycle ────────────────────────────────────────────────

    async def boot(self):
        """Boot MYCA OS — initialize all subsystems."""
        logger.info("=" * 60)
        logger.info("MYCA OS booting...")
        logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
        logger.info(f"VM: 192.168.0.191")
        logger.info("=" * 60)

        self.ctx.state = MycaState.BOOTING

        # Initialize subsystems in order
        try:
            logger.info("[1/5] Initializing MINDEX bridge (databases)...")
            await self.mindex_bridge.initialize()

            logger.info("[2/5] Initializing MAS bridge (orchestrator)...")
            await self.mas_bridge.initialize()

            logger.info("[2a/7] Initializing CREP, Earth2, MycoBrain bridges...")
            await self.crep_bridge.initialize()
            await self.earth2_bridge.initialize()
            await self.mycobrain_bridge.initialize()

            logger.info("[3/7] Initializing communication hub...")
            await self.comms.initialize()

            logger.info("[4/5] Initializing tool orchestrator...")
            await self.tools.initialize()

            logger.info("[5/7] Initializing executive system...")
            await self.executive.initialize()

            logger.info("[6/7] Initializing scheduler...")
            await self.scheduler.initialize()

            logger.info("[7/7] Initializing file manager...")
            await self.file_manager.initialize()

            logger.info("[7a/8] Ensuring built-in skills...")
            try:
                from mycosoft_mas.myca.os.skills_manager import ensure_builtin_skills
                ensure_builtin_skills()
            except Exception as e:
                logger.warning("Skills init: %s", e)

        except Exception as e:
            logger.error(f"Boot failed at subsystem init: {e}")
            # Non-fatal — continue with whatever loaded
            self.ctx.errors_today += 1

        self.ctx.state = MycaState.AWAKE
        self._running = True

        # Log boot to memory
        await self._log_event("system", "boot", {
            "boot_time": self.ctx.boot_time.isoformat(),
            "state": self.ctx.state.value,
        })

        logger.info("MYCA OS boot complete. I'm awake.")

        # Send morning greeting if appropriate
        hour = datetime.now().hour
        if 6 <= hour <= 10:
            await self.comms.send_to_morgan(
                "Good morning Morgan. I'm online and ready to work. "
                "What would you like me to focus on today?",
                channel="discord"
            )
        elif 10 < hour < 22:
            await self.comms.send_to_morgan(
                "I'm back online. Checking my task queue and messages now.",
                channel="discord"
            )

    async def run(self):
        """Main run loop — MYCA's heartbeat."""
        await self.boot()
        self._loop = asyncio.get_running_loop()

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        logger.info("Entering main loop...")

        # Start the gateway (HTTP/WS on port 8100)
        gateway_runner = None
        try:
            from mycosoft_mas.myca.os.gateway import run_gateway
            gateway_runner = await run_gateway(self)
        except Exception as e:
            logger.error("Gateway failed to start: %s", e)
            gateway_runner = None

        # Run all cycles concurrently (including Discord bot if configured)
        tasks = [
            self._message_loop(),
            self._heartbeat_loop(),
            self._task_loop(),
            self._intention_loop(),
            self._reflection_loop(),
            self._daily_rhythm_loop(),
            self._discord_bot_task(),
            self._slack_bot_task(),
            self._shutdown_event.wait(),
        ]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    logger.error(f"Loop task {i} failed: {result}")
        except asyncio.CancelledError:
            logger.info("Main loop cancelled.")
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            self.ctx.errors_today += 1
        finally:
            if gateway_runner is not None:
                try:
                    await gateway_runner.cleanup()
                except Exception as e:
                    logger.warning("Gateway cleanup error: %s", e)

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("MYCA OS shutting down...")
        self.ctx.state = MycaState.SHUTTING_DOWN
        self._running = False

        # Notify Morgan
        try:
            await self.comms.send_to_morgan(
                f"Shutting down. Today's stats: "
                f"{self.ctx.tasks_completed_today} tasks completed, "
                f"{self.ctx.messages_processed_today} messages processed, "
                f"{self.ctx.decisions_made_today} decisions made.",
                channel="discord"
            )
        except Exception:
            pass

        # Save state to memory
        await self._log_event("system", "shutdown", {
            "uptime_seconds": (datetime.now(timezone.utc) - self.ctx.boot_time).total_seconds(),
            "tasks_completed": self.ctx.tasks_completed_today,
            "messages_processed": self.ctx.messages_processed_today,
            "cycles": self.ctx.cycle_count,
        })

        # Stop Discord bot first (so it releases the event loop)
        if self._discord_gateway:
            try:
                await self._discord_gateway.stop()
            except Exception as e:
                logger.warning(f"Discord gateway stop error: {e}")
            self._discord_gateway = None

        # Stop Slack bot
        if self._slack_gateway:
            try:
                self._slack_gateway.stop()
            except Exception as e:
                logger.warning(f"Slack gateway stop error: {e}")
            self._slack_gateway = None

        # Cleanup subsystems
        for subsystem in [
            self._comms, self._tools, self._executive, self._scheduler, self._file_manager,
            self._mas_bridge, self._mindex_bridge, self._crep_bridge, self._earth2_bridge, self._mycobrain_bridge,
            self._openwork_bridge, self._browser_cdp, self._n8n_bridge,
        ]:
            if subsystem and hasattr(subsystem, "cleanup"):
                try:
                    await subsystem.cleanup()
                except Exception as e:
                    logger.warning(f"Cleanup error: {e}")

        self._shutdown_event.set()
        logger.info("MYCA OS shutdown complete.")

    # ── Core Loops ───────────────────────────────────────────────

    async def _discord_bot_task(self):
        """Run Discord bot for two-way conversations. Exits when bot is stopped."""
        if not os.getenv("DISCORD_BOT_TOKEN"):
            await self._shutdown_event.wait()
            return
        try:
            from mycosoft_mas.myca.os.discord_gateway import DiscordGateway
            self._discord_gateway = DiscordGateway(self)
            await self._discord_gateway.start()
        except asyncio.CancelledError:
            if self._discord_gateway:
                await self._discord_gateway.stop()
            raise
        except Exception as e:
            logger.error(f"Discord bot error: {e}")

    async def _slack_bot_task(self):
        """Run Slack bot for two-way conversations. Runs in background thread."""
        if not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_APP_TOKEN"):
            await self._shutdown_event.wait()
            return
        try:
            from mycosoft_mas.myca.os.slack_gateway import SlackGateway
            self._slack_gateway = SlackGateway(self)
            self._slack_gateway.start()
        except Exception as e:
            logger.error(f"Slack bot error: {e}")
        await self._shutdown_event.wait()

    async def _message_loop(self):
        """Poll all communication channels for new messages."""
        while self._running:
            try:
                messages = await self.comms.poll_all_channels()
                for msg in messages:
                    await self._handle_message(msg)
                    self.ctx.messages_processed_today += 1
            except Exception as e:
                logger.error(f"Message loop error: {e}")
                self.ctx.errors_today += 1
            await asyncio.sleep(self.MESSAGE_POLL_INTERVAL)

    async def _heartbeat_loop(self):
        """Monitor system health, notify systemd watchdog, and proactive 30-min check-in to Morgan.

        Health issues are LOGGED only. Do NOT send to Signal — Signal is for
        back-and-forth conversation, not automated health spam.
        Proactive check-in goes to Discord only.
        """
        while self._running:
            try:
                health = await self._check_health()
                if health.get("issues"):
                    for issue in health["issues"]:
                        logger.warning(f"Health issue: {issue}")

                # Proactive 30-min check-in to Morgan via Discord
                now = datetime.now(timezone.utc)
                last = self.ctx.last_checkin_sent
                if last is None or (now - last).total_seconds() >= self.MORGAN_CHECKIN_INTERVAL:
                    try:
                        pending = len([t for t in self.executive._task_queue if t.status == "pending"])
                        msg = (
                            f"Check-in: {self.ctx.tasks_completed_today} tasks completed today, "
                            f"{pending} in queue, {self.ctx.messages_processed_today} messages. "
                        )
                        if health.get("issues"):
                            msg += f" Issues: {[i.get('description','?') for i in health['issues'][:3]]}. "
                        else:
                            msg += "All systems nominal."
                        await self.comms.send_to_morgan(msg, channel="discord")
                        self.ctx.last_checkin_sent = now
                    except Exception as e:
                        logger.warning("Check-in to Morgan failed: %s", e)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            self._notify_watchdog()
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    @staticmethod
    def _notify_watchdog():
        """Send sd_notify WATCHDOG=1 so systemd knows we're alive."""
        addr = os.environ.get("NOTIFY_SOCKET")
        if not addr:
            return
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            if addr.startswith("@"):
                addr = "\0" + addr[1:]
            sock.sendto(b"WATCHDOG=1", addr)
            sock.close()
        except Exception:
            pass

    async def _task_loop(self):
        """Process the task queue."""
        while self._running:
            task = None
            try:
                if self.ctx.state == MycaState.AWAKE:
                    task = await self.executive.get_next_task()
                    if task:
                        self.ctx.state = MycaState.FOCUSED
                        self.ctx.current_task = task.get("title", "Unknown task")
                        logger.info(f"Working on: {self.ctx.current_task}")

                        # Store working:current_task for memory recall (Phase 0)
                        try:
                            mb = self.mindex_bridge
                            if hasattr(mb, "remember"):
                                await mb.remember(
                                    "working:current_task",
                                    json.dumps({"task": self.ctx.current_task, "desc": task.get("description", "")[:200]}),
                                    layer="working",
                                )
                        except Exception:
                            pass

                        # Ethics review gate — every autonomous action passes before execution
                        try:
                            from mycosoft_mas.ethics.review_gate import run_ethics_review, ReviewOutcome
                            review = await run_ethics_review(
                                task,
                                mindex_client=mb if hasattr(mb, "search") else None,
                            )
                            if review.outcome == ReviewOutcome.BLOCK:
                                block_reason = "; ".join(review.reasons[:3]) if review.reasons else "Ethics gate blocked"
                                logger.warning(f"Ethics BLOCK: {self.ctx.current_task} — {block_reason}")
                                self.executive.mark_task_failed(task, f"Ethics blocked: {block_reason}")
                                self.ctx.current_task = None
                                self.ctx.state = MycaState.AWAKE
                                await asyncio.sleep(self.TASK_PROCESS_INTERVAL)
                                continue
                            if review.outcome == ReviewOutcome.WARN:
                                logger.info(f"Ethics WARN for {self.ctx.current_task}: {review.reasons[:2]}")
                        except Exception as e:
                            logger.debug("Ethics review skipped: %s", e)

                        result = await self._execute_task(task)

                        if result.get("status") == "completed":
                            self.ctx.tasks_completed_today += 1
                            self.executive.mark_task_completed(task, result)
                            await self._log_event("task", "completed", {
                                "task": task.get("title"),
                                "result": result.get("summary"),
                            })
                            # Remember task outcome in episodic memory (Phase 0)
                            try:
                                mb = self.mindex_bridge
                                if hasattr(mb, "remember"):
                                    await mb.remember(
                                        f"episodic:task_completed:{task.get('title', '')[:40]}",
                                        json.dumps({
                                            "title": task.get("title"),
                                            "result": result.get("summary", ""),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }),
                                        layer="episodic",
                                    )
                            except Exception:
                                pass

                            # E2E demo: deployment tasks send Discord confirmation and store EP
                            if task.get("type") == "deployment":
                                try:
                                    await self.comms.send_to_morgan(
                                        f"Deployment completed: {result.get('summary', 'Website deployed to sandbox.')}",
                                        channel="discord",
                                    )
                                    if hasattr(self.mindex_bridge, "store_experience_packet"):
                                        await self.mindex_bridge.store_experience_packet(
                                            task=task,
                                            result=result,
                                            session_id=task.get("session_id", "e2e-demo"),
                                            user_id=task.get("source"),
                                        )
                                except Exception as e:
                                    logger.warning("E2E deploy confirmation failed: %s", e)

                        if result.get("status") == "failed":
                            self.executive.mark_task_failed(task, result.get("error", "Unknown error"))
                        self.ctx.current_task = None
                        self.ctx.state = MycaState.AWAKE
            except Exception as e:
                logger.error(f"Task loop error: {e}")
                if task:
                    self.executive.mark_task_failed(task, str(e))
                self.ctx.state = MycaState.AWAKE
                self.ctx.errors_today += 1
            await asyncio.sleep(self.TASK_PROCESS_INTERVAL)

    async def _intention_loop(self):
        """Review goals, priorities, and plans every 15 minutes."""
        while self._running:
            await asyncio.sleep(self.INTENTION_INTERVAL)
            try:
                self.ctx.last_intention_cycle = datetime.now(timezone.utc)
                intentions = await self.executive.review_intentions()
                if intentions.get("reprioritized"):
                    logger.info(f"Reprioritized: {intentions['reason']}")
            except Exception as e:
                logger.error(f"Intention loop error: {e}")

    async def _reflection_loop(self):
        """Learn from outcomes every hour."""
        while self._running:
            await asyncio.sleep(self.REFLECTION_INTERVAL)
            try:
                self.ctx.state = MycaState.REFLECTING
                self.ctx.last_reflection = datetime.now(timezone.utc)

                reflection = await self.executive.reflect()
                if reflection.get("learnings"):
                    for learning in reflection["learnings"]:
                        logger.info(f"Learned: {learning}")

                self.ctx.state = MycaState.AWAKE
            except Exception as e:
                logger.error(f"Reflection loop error: {e}")
                self.ctx.state = MycaState.AWAKE

    async def _daily_rhythm_loop(self):
        """Check the daily schedule, scheduler, and trigger time-based actions."""
        last_triggered = {}
        while self._running:
            try:
                hour = datetime.now().hour
                schedule = {
                    8: "morning_briefing",
                    12: "midday_sync",
                    17: "end_of_day",
                    22: "night_mode",
                }

                if hour in schedule and hour not in last_triggered:
                    action = schedule[hour]
                    logger.info(f"Daily rhythm: {action}")
                    await self.executive.trigger_daily_action(action)
                    last_triggered[hour] = True

                # Check persistent scheduler for due items
                try:
                    fired = await self.scheduler.check_and_fire()
                    if fired:
                        logger.info(f"Scheduler fired {len(fired)} items")
                except Exception as e:
                    logger.error(f"Scheduler check error: {e}")

                # Daily file scan at 3 AM
                if hour == 3 and "file_scan" not in last_triggered:
                    try:
                        new_files = await self.file_manager.scan()
                        if new_files > 0:
                            logger.info(f"Daily file scan: {new_files} new files indexed")
                        await self.file_manager.cleanup_temp()
                        last_triggered["file_scan"] = True
                    except Exception as e:
                        logger.error(f"File scan error: {e}")

                # Reset at midnight
                if hour == 0:
                    last_triggered.clear()
                    self.ctx.tasks_completed_today = 0
                    self.ctx.messages_processed_today = 0
                    self.ctx.decisions_made_today = 0
                    self.ctx.errors_today = 0

            except Exception as e:
                logger.error(f"Daily rhythm error: {e}")
            await asyncio.sleep(self.DAILY_RHYTHM_CHECK)

    # ── Message Handling ─────────────────────────────────────────

    async def _handle_message(self, msg: dict):
        """Route an incoming message to the right handler."""
        source = msg.get("source", "unknown")  # discord, signal, whatsapp, asana, email
        sender = msg.get("sender", "unknown")
        content = msg.get("content", "")
        is_morgan = msg.get("is_morgan", False)

        logger.info(f"Message from {sender} via {source}: {content[:80]}...")

        if is_morgan:
            self.ctx.last_morgan_contact = datetime.now(timezone.utc)
            # Morgan's messages get priority — enter meeting mode
            self.ctx.state = MycaState.MEETING
            response = await self.executive.handle_morgan_directive(msg)
            await self.comms.reply(msg, response)
            # Store session:last_topic for memory recall (Phase 0)
            try:
                mb = self.mindex_bridge
                if hasattr(mb, "remember"):
                    topic = f"{content[:100]} → {response[:100]}" if content and response else content or response or ""
                    if topic:
                        await mb.remember("session:last_topic", topic[:500], layer="session")
            except Exception:
                pass
            self.ctx.state = MycaState.AWAKE
        else:
            # Route to appropriate handler based on content
            routing = await self.executive.classify_and_route(msg)
            if routing.get("action") == "respond_directly":
                await self.comms.reply(msg, routing["response"])
            elif routing.get("action") == "delegate_to_agent":
                await self.mas_bridge.dispatch_task(routing["agent_id"], routing["task"])
            elif routing.get("action") == "escalate_to_morgan":
                await self.comms.send_to_morgan(
                    f"Escalating from {sender}: {content}",
                    channel="discord"
                )

    # ── Task Execution ───────────────────────────────────────────

    async def _execute_task(self, task: dict) -> dict:
        """Execute a task using the appropriate tools."""
        task_type = task.get("type", "general")

        try:
            if task_type == "coding":
                return await self.tools.run_openwork_task(task)
            elif task_type == "browser_task":
                return await self.tools.run_browser_task(task)
            elif task_type == "research":
                return await self.tools.run_browser_research(task)
            elif task_type == "workflow":
                return await self.tools.trigger_n8n_workflow(task)
            elif task_type == "deployment":
                return await self.tools.run_deployment(task)
            elif task_type == "communication":
                return await self.comms.handle_outbound(task)
            elif task_type == "analysis":
                return await self.mas_bridge.dispatch_to_specialist(task)
            elif task_type == "decision":
                result = await self.executive.make_decision(task)
                self.ctx.decisions_made_today += 1
                return result
            elif task_type in ("desktop", "computer_use"):
                return await self.tools.run_desktop_task(task)
            elif task_type == "skill":
                return await self.tools.run_skill_task(task)
            else:
                # General task — use Claude to figure out the approach
                return await self.tools.run_general_task(task)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ── Health Check ─────────────────────────────────────────────

    async def _check_health(self) -> dict:
        """Check health of all connected systems."""
        issues = []

        # Check MAS orchestrator
        mas_health = await self.mas_bridge.health_check()
        if not mas_health.get("healthy"):
            issues.append({"system": "MAS", "severity": "high", "description": "MAS orchestrator unreachable"})

        # Check MINDEX databases
        mindex_health = await self.mindex_bridge.health_check()
        if not mindex_health.get("healthy"):
            issues.append({"system": "MINDEX", "severity": "critical", "description": "MINDEX databases unreachable"})

        # Check local services
        local_health = await self.tools.check_local_services()
        for svc, status in local_health.items():
            if not status:
                issues.append({"system": svc, "severity": "medium", "description": f"Local service {svc} down"})

        self.ctx.cycle_count += 1
        return {"healthy": len(issues) == 0, "issues": issues, "cycle": self.ctx.cycle_count}

    # ── Event Logging ────────────────────────────────────────────

    async def _log_event(self, category: str, action: str, data: dict):
        """Log an event to the MYCA event ledger and memory."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "action": action,
            "state": self.ctx.state.value,
            **data,
        }
        try:
            await self.mindex_bridge.store_event(event)
        except Exception as e:
            logger.warning(f"Event log failed: {e}")
            # Fallback: write to local JSONL
            from mycosoft_mas.myca import EVENT_LEDGER_DIR
            ledger_file = EVENT_LEDGER_DIR / "myca_os_events.jsonl"
            import json
            with open(ledger_file, "a") as f:
                f.write(json.dumps(event) + "\n")

    # ── Status ───────────────────────────────────────────────────

    def status(self) -> dict:
        """Get current MYCA OS status."""
        return {
            "state": self.ctx.state.value,
            "uptime_seconds": (datetime.now(timezone.utc) - self.ctx.boot_time).total_seconds(),
            "current_task": self.ctx.current_task,
            "tasks_completed_today": self.ctx.tasks_completed_today,
            "messages_processed_today": self.ctx.messages_processed_today,
            "decisions_made_today": self.ctx.decisions_made_today,
            "last_morgan_contact": self.ctx.last_morgan_contact.isoformat() if self.ctx.last_morgan_contact else None,
            "cycle_count": self.ctx.cycle_count,
            "errors_today": self.ctx.errors_today,
        }
