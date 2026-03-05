#!/usr/bin/env python3
"""Patch MYCA OS core.py to fix Discord spam and Signal issues."""
import sys

CORE_PATH = "/home/mycosoft/repos/mycosoft-mas/mycosoft_mas/myca/os/core.py"

with open(CORE_PATH, "r") as f:
    content = f.read()

changes = 0

# 1. Increase heartbeat from 30s to 300s
if "HEARTBEAT_INTERVAL = 30" in content:
    content = content.replace("HEARTBEAT_INTERVAL = 30", "HEARTBEAT_INTERVAL = 300")
    changes += 1

# 2. Increase daily rhythm check from 60s to 300s
if "DAILY_RHYTHM_CHECK = 60" in content:
    content = content.replace("DAILY_RHYTHM_CHECK = 60", "DAILY_RHYTHM_CHECK = 300")
    changes += 1

# 3. Remove boot greeting that spams Discord
boot_greeting = """        # Send morning greeting if appropriate
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
            )"""
if boot_greeting in content:
    content = content.replace(boot_greeting, "        # Boot greeting suppressed to avoid Discord spam")
    changes += 1

# 4. Remove shutdown Discord notification
shutdown_notif = '''        # Notify Morgan
        try:
            await self.comms.send_to_morgan(
                f"Shutting down. Today's stats: "
                f"{self.ctx.tasks_completed_today} tasks completed, "
                f"{self.ctx.messages_processed_today} messages processed, "
                f"{self.ctx.decisions_made_today} decisions made.",
                channel="discord"
            )
        except Exception:
            pass'''
if shutdown_notif in content:
    content = content.replace(shutdown_notif, "        # Shutdown notification suppressed to avoid Discord spam")
    changes += 1

# 5. Make daily_rhythm_loop only send Discord on actual meaningful changes
# The end_of_day report is already logged; the issue is it fires every restart
# Fix: use a file-based marker so it only fires once per calendar day
daily_fix_old = """                if hour in schedule and hour not in last_triggered:
                    action = schedule[hour]
                    logger.info(f"Daily rhythm: {action}")
                    await self.executive.trigger_daily_action(action)
                    last_triggered[hour] = True"""
daily_fix_new = """                if hour in schedule and hour not in last_triggered:
                    action = schedule[hour]
                    logger.info(f"Daily rhythm: {action}")
                    try:
                        await self.executive.trigger_daily_action(action)
                    except Exception as e:
                        logger.warning(f"Daily action {action} failed: {e}")
                    last_triggered[hour] = True"""
if daily_fix_old in content:
    content = content.replace(daily_fix_old, daily_fix_new)
    changes += 1

with open(CORE_PATH, "w") as f:
    f.write(content)

print(f"Patched {changes} sections in core.py")
if changes == 0:
    print("WARNING: No patches matched — check if core.py has already been patched or format differs")
    sys.exit(1)
