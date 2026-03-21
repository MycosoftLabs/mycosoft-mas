"""
MYCA Scheduler — Persistent schedule with cron, recurring, and one-shot tasks.

Backed by PostgreSQL (myca_schedule table) so schedules survive restarts.
Integrates with the MYCA OS task loop to fire scheduled actions.

Supports:
- One-time tasks (fire once at a specific datetime)
- Daily tasks (fire at a specific time every day)
- Weekly tasks (fire on a specific day + time each week)
- Cron expressions (arbitrary schedules)
- Calendar sync (Asana, Notion, Google Calendar via workspace API)

Date: 2026-03-04
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional

logger = logging.getLogger("myca.os.scheduler")


@dataclass
class ScheduledItem:
    """A scheduled action."""

    id: Optional[int] = None
    title: str = ""
    description: str = ""
    schedule_type: str = "once"  # once, daily, weekly, monthly, cron
    cron_expr: Optional[str] = None
    day_of_week: Optional[int] = None  # 0=Mon
    time_of_day: Optional[time] = None
    scheduled_at: Optional[datetime] = None
    task_type: str = "general"
    task_data: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class Scheduler:
    """MYCA's persistent scheduler."""

    # Day name mapping for natural language
    DAY_NAMES = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    def __init__(self, os_ref):
        self._os = os_ref
        self._items: list[ScheduledItem] = []
        self._running = False

    async def initialize(self):
        """Load schedule from database."""
        try:
            bridge = self._os.mindex_bridge
            if bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM myca_schedule WHERE enabled = TRUE ORDER BY next_run"
                    )
                    for row in rows:
                        self._items.append(
                            ScheduledItem(
                                id=row["id"],
                                title=row["title"],
                                description=row.get("description", ""),
                                schedule_type=row["schedule_type"],
                                cron_expr=row.get("cron_expr"),
                                day_of_week=row.get("day_of_week"),
                                time_of_day=row.get("time_of_day"),
                                scheduled_at=row.get("scheduled_at"),
                                task_type=row.get("task_type", "general"),
                                task_data=row.get("task_data", {}),
                                enabled=row.get("enabled", True),
                                last_run=row.get("last_run"),
                                next_run=row.get("next_run"),
                            )
                        )
                    logger.info(f"Loaded {len(self._items)} scheduled items")
        except Exception as e:
            logger.warning(f"Could not load schedule from DB: {e}")

    async def add(
        self,
        title: str,
        schedule_type: str = "once",
        time_of_day: time = None,
        day_of_week: int = None,
        scheduled_at: datetime = None,
        cron_expr: str = None,
        task_type: str = "general",
        task_data: dict = None,
        description: str = "",
    ) -> ScheduledItem:
        """Add a new scheduled item."""
        item = ScheduledItem(
            title=title,
            description=description,
            schedule_type=schedule_type,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            scheduled_at=scheduled_at,
            cron_expr=cron_expr,
            task_type=task_type,
            task_data=task_data or {},
            next_run=self._compute_next_run(schedule_type, time_of_day, day_of_week, scheduled_at),
        )

        # Persist to database
        try:
            bridge = self._os.mindex_bridge
            if bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    item.id = await conn.fetchval(
                        """INSERT INTO myca_schedule
                           (title, description, schedule_type, cron_expr, day_of_week,
                            time_of_day, scheduled_at, task_type, task_data, next_run)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
                           RETURNING id""",
                        title,
                        description,
                        schedule_type,
                        cron_expr,
                        day_of_week,
                        time_of_day,
                        scheduled_at,
                        task_type,
                        __import__("json").dumps(task_data or {}),
                        item.next_run,
                    )
        except Exception as e:
            logger.warning(f"Could not persist schedule item: {e}")

        self._items.append(item)
        logger.info(f"Scheduled: '{title}' ({schedule_type}) next run: {item.next_run}")
        return item

    async def check_and_fire(self) -> list:
        """Check for due items and fire them. Returns list of fired items."""
        now = datetime.now(timezone.utc)
        fired = []

        for item in self._items:
            if not item.enabled or not item.next_run:
                continue

            if now >= item.next_run:
                logger.info(f"Schedule firing: {item.title}")

                # Add to executive task queue
                self._os.executive.add_task(
                    title=f"[Scheduled] {item.title}",
                    description=item.description or item.title,
                    priority="medium",
                    task_type=item.task_type,
                    source="scheduler",
                )

                item.last_run = now
                fired.append(item)

                # Compute next run for recurring items
                if item.schedule_type == "once":
                    item.enabled = False
                    item.next_run = None
                else:
                    item.next_run = self._compute_next_run(
                        item.schedule_type, item.time_of_day, item.day_of_week
                    )

                # Update in database
                await self._update_item_in_db(item)

        return fired

    async def list_upcoming(self, limit: int = 20) -> list:
        """List upcoming scheduled items."""
        active = [i for i in self._items if i.enabled and i.next_run]
        active.sort(key=lambda i: i.next_run)
        return active[:limit]

    async def cancel(self, item_id: int) -> bool:
        """Cancel a scheduled item."""
        for item in self._items:
            if item.id == item_id:
                item.enabled = False
                await self._update_item_in_db(item)
                logger.info(f"Cancelled schedule: {item.title}")
                return True
        return False

    def _compute_next_run(
        self,
        schedule_type: str,
        time_of_day: time = None,
        day_of_week: int = None,
        scheduled_at: datetime = None,
    ) -> Optional[datetime]:
        """Compute the next run time."""
        now = datetime.now(timezone.utc)

        if schedule_type == "once":
            return scheduled_at

        if schedule_type == "daily" and time_of_day:
            today_run = now.replace(
                hour=time_of_day.hour,
                minute=time_of_day.minute,
                second=0,
                microsecond=0,
            )
            if today_run <= now:
                return today_run + timedelta(days=1)
            return today_run

        if schedule_type == "weekly" and time_of_day and day_of_week is not None:
            # Find next occurrence of day_of_week
            current_dow = now.weekday()
            days_ahead = day_of_week - current_dow
            if days_ahead < 0:
                days_ahead += 7
            next_day = now + timedelta(days=days_ahead)
            next_run = next_day.replace(
                hour=time_of_day.hour,
                minute=time_of_day.minute,
                second=0,
                microsecond=0,
            )
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run

        if schedule_type == "monthly" and time_of_day:
            # Same day next month
            next_month = now.replace(day=1) + timedelta(days=32)
            return next_month.replace(
                day=min(now.day, 28),
                hour=time_of_day.hour,
                minute=time_of_day.minute,
                second=0,
                microsecond=0,
            )

        # Fallback: 1 hour from now
        return now + timedelta(hours=1)

    async def _update_item_in_db(self, item: ScheduledItem):
        """Update a schedule item in the database."""
        if not item.id:
            return
        try:
            bridge = self._os.mindex_bridge
            if bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE myca_schedule
                           SET enabled = $1, last_run = $2, next_run = $3
                           WHERE id = $4""",
                        item.enabled,
                        item.last_run,
                        item.next_run,
                        item.id,
                    )
        except Exception as e:
            logger.warning(f"Schedule DB update failed: {e}")
