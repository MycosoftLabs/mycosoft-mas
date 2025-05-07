"""
Schedule Manager for Secretary Agent

This module implements a comprehensive scheduling and presence detection system
for the Secretary Agent to manage user schedules, detect presence, and determine
appropriate notification timing.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from pathlib import Path
from enum import Enum, auto

from ..messaging.message_types import MessagePriority

class ActivityType(Enum):
    """Types of activities that can be scheduled or detected"""
    SLEEP = auto()
    WAKE = auto()
    WORK = auto()
    MEAL = auto()
    EXERCISE = auto()
    LEISURE = auto()
    MEETING = auto()
    TRAVEL = auto()
    CUSTOM = auto()

class LocationType(Enum):
    """Types of locations where presence can be detected"""
    BEDROOM = auto()
    LAB = auto()
    OFFICE = auto()
    KITCHEN = auto()
    LIVING_ROOM = auto()
    BATHROOM = auto()
    OUTSIDE = auto()
    TRAVELING = auto()
    UNKNOWN = auto()

class PresenceSource(Enum):
    """Sources of presence detection"""
    PHONE = auto()
    SMARTWATCH = auto()
    MICROPHONE = auto()
    THERMOSTAT = auto()
    MOTION_SENSOR = auto()
    CAMERA = auto()
    DOOR_SENSOR = auto()
    LIGHT_SENSOR = auto()
    COMPUTER = auto()
    MANUAL = auto()

class NotificationPreference(Enum):
    """User preferences for notifications"""
    ALWAYS = auto()
    WORKING_HOURS = auto()
    AWAKE = auto()
    HIGH_PRIORITY = auto()
    NEVER = auto()

class ScheduleManager:
    """
    Manages user schedules, presence detection, and notification timing.
    
    This class handles:
    1. Daily/weekly schedules (sleep, wake, work, meals, etc.)
    2. Presence detection from various devices
    3. Notification preferences and timing
    4. Integration with the messaging system
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the schedule manager.
        
        Args:
            config: Configuration dictionary for the schedule manager
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create data directory
        self.data_dir = Path("data/secretary/schedule")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Schedule data
        self.daily_schedule: Dict[str, Dict[str, Any]] = {}
        self.weekly_schedule: Dict[str, Dict[str, Any]] = {}
        self.special_dates: Dict[str, Dict[str, Any]] = {}
        
        # Presence data
        self.current_location: LocationType = LocationType.UNKNOWN
        self.current_activity: ActivityType = ActivityType.CUSTOM
        self.presence_sources: Dict[PresenceSource, bool] = {}
        self.last_presence_update: Dict[PresenceSource, datetime] = {}
        
        # Notification preferences
        self.notification_preferences: Dict[str, NotificationPreference] = {}
        
        # Metrics
        self.metrics = {
            "schedule_updates": 0,
            "presence_updates": 0,
            "notifications_sent": 0,
            "notifications_delayed": 0,
            "notifications_skipped": 0
        }
        
        # Load data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load schedule and presence data from disk"""
        try:
            # Load daily schedule
            daily_file = self.data_dir / "daily_schedule.json"
            if daily_file.exists():
                with open(daily_file, "r") as f:
                    self.daily_schedule = json.load(f)
            
            # Load weekly schedule
            weekly_file = self.data_dir / "weekly_schedule.json"
            if weekly_file.exists():
                with open(weekly_file, "r") as f:
                    self.weekly_schedule = json.load(f)
            
            # Load special dates
            special_file = self.data_dir / "special_dates.json"
            if special_file.exists():
                with open(special_file, "r") as f:
                    self.special_dates = json.load(f)
            
            # Load notification preferences
            prefs_file = self.data_dir / "notification_preferences.json"
            if prefs_file.exists():
                with open(prefs_file, "r") as f:
                    prefs_data = json.load(f)
                    self.notification_preferences = {
                        k: NotificationPreference[v] for k, v in prefs_data.items()
                    }
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading schedule data: {str(e)}")
    
    async def save_data(self) -> None:
        """Save schedule and presence data to disk"""
        try:
            # Save daily schedule
            daily_file = self.data_dir / "daily_schedule.json"
            with open(daily_file, "w") as f:
                json.dump(self.daily_schedule, f, indent=2)
            
            # Save weekly schedule
            weekly_file = self.data_dir / "weekly_schedule.json"
            with open(weekly_file, "w") as f:
                json.dump(self.weekly_schedule, f, indent=2)
            
            # Save special dates
            special_file = self.data_dir / "special_dates.json"
            with open(special_file, "w") as f:
                json.dump(self.special_dates, f, indent=2)
            
            # Save notification preferences
            prefs_file = self.data_dir / "notification_preferences.json"
            with open(prefs_file, "w") as f:
                json.dump({
                    k: v.name for k, v in self.notification_preferences.items()
                }, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving schedule data: {str(e)}")
    
    async def start(self) -> None:
        """Start the schedule manager"""
        self.logger.info("Starting schedule manager")
        
        # Start background tasks
        asyncio.create_task(self._periodic_save())
        asyncio.create_task(self._check_schedule())
        
        self.logger.info("Schedule manager started")
    
    async def stop(self) -> None:
        """Stop the schedule manager"""
        self.logger.info("Stopping schedule manager")
        
        # Save data
        await self.save_data()
        
        self.logger.info("Schedule manager stopped")
    
    # Schedule Management Methods
    
    async def set_daily_schedule(
        self,
        activity: ActivityType,
        start_time: time,
        end_time: time,
        days: List[str] = None
    ) -> None:
        """
        Set a daily schedule for an activity.
        
        Args:
            activity: Type of activity
            start_time: Start time of the activity
            end_time: End time of the activity
            days: List of days (mon, tue, wed, thu, fri, sat, sun) or None for all days
        """
        activity_id = str(uuid.uuid4())
        
        schedule_entry = {
            "activity": activity.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "days": days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        }
        
        self.daily_schedule[activity_id] = schedule_entry
        self.metrics["schedule_updates"] += 1
        
        await self.save_data()
    
    async def set_weekly_schedule(
        self,
        activity: ActivityType,
        day_of_week: str,
        start_time: time,
        end_time: time
    ) -> None:
        """
        Set a weekly schedule for an activity.
        
        Args:
            activity: Type of activity
            day_of_week: Day of the week (mon, tue, wed, thu, fri, sat, sun)
            start_time: Start time of the activity
            end_time: End time of the activity
        """
        activity_id = str(uuid.uuid4())
        
        schedule_entry = {
            "activity": activity.name,
            "day_of_week": day_of_week,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        self.weekly_schedule[activity_id] = schedule_entry
        self.metrics["schedule_updates"] += 1
        
        await self.save_data()
    
    async def set_special_date(
        self,
        date: datetime,
        activity: ActivityType,
        start_time: time,
        end_time: time,
        description: str = ""
    ) -> None:
        """
        Set a special date schedule (holidays, vacations, etc.).
        
        Args:
            date: Date of the special schedule
            activity: Type of activity
            start_time: Start time of the activity
            end_time: End time of the activity
            description: Description of the special date
        """
        date_str = date.strftime("%Y-%m-%d")
        
        special_entry = {
            "activity": activity.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": description
        }
        
        self.special_dates[date_str] = special_entry
        self.metrics["schedule_updates"] += 1
        
        await self.save_data()
    
    async def get_current_schedule(self) -> Dict[str, Any]:
        """
        Get the current schedule based on the current time.
        
        Returns:
            Dict containing the current schedule information
        """
        now = datetime.now()
        day_of_week = now.strftime("%a").lower()
        time_str = now.strftime("%H:%M:%S")
        
        # Check special dates first
        date_str = now.strftime("%Y-%m-%d")
        if date_str in self.special_dates:
            special = self.special_dates[date_str]
            start_time = datetime.fromisoformat(special["start_time"]).time()
            end_time = datetime.fromisoformat(special["end_time"]).time()
            
            if start_time <= now.time() <= end_time:
                return {
                    "type": "special",
                    "activity": ActivityType[special["activity"]],
                    "description": special.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time
                }
        
        # Check daily schedule
        for activity_id, schedule in self.daily_schedule.items():
            if day_of_week in schedule["days"]:
                start_time = datetime.fromisoformat(schedule["start_time"]).time()
                end_time = datetime.fromisoformat(schedule["end_time"]).time()
                
                if start_time <= now.time() <= end_time:
                    return {
                        "type": "daily",
                        "activity": ActivityType[schedule["activity"]],
                        "start_time": start_time,
                        "end_time": end_time
                    }
        
        # Check weekly schedule
        for activity_id, schedule in self.weekly_schedule.items():
            if schedule["day_of_week"] == day_of_week:
                start_time = datetime.fromisoformat(schedule["start_time"]).time()
                end_time = datetime.fromisoformat(schedule["end_time"]).time()
                
                if start_time <= now.time() <= end_time:
                    return {
                        "type": "weekly",
                        "activity": ActivityType[schedule["activity"]],
                        "start_time": start_time,
                        "end_time": end_time
                    }
        
        # Default to custom activity if no schedule matches
        return {
            "type": "default",
            "activity": ActivityType.CUSTOM,
            "start_time": None,
            "end_time": None
        }
    
    # Presence Detection Methods
    
    async def update_presence(
        self,
        source: PresenceSource,
        location: LocationType,
        activity: Optional[ActivityType] = None
    ) -> None:
        """
        Update presence information from a detection source.
        
        Args:
            source: Source of the presence detection
            location: Detected location
            activity: Detected activity (optional)
        """
        self.presence_sources[source] = True
        self.last_presence_update[source] = datetime.now()
        
        # Update current location if more than one source confirms
        confirmed_sources = sum(1 for v in self.presence_sources.values() if v)
        if confirmed_sources >= 2:
            self.current_location = location
            
            # Update activity if provided
            if activity:
                self.current_activity = activity
        
        self.metrics["presence_updates"] += 1
        
        await self.save_data()
    
    async def clear_presence(self, source: PresenceSource) -> None:
        """
        Clear presence information from a detection source.
        
        Args:
            source: Source of the presence detection
        """
        self.presence_sources[source] = False
        
        # Check if we need to update current location
        active_sources = [s for s, v in self.presence_sources.items() if v]
        if len(active_sources) < 2:
            self.current_location = LocationType.UNKNOWN
        
        await self.save_data()
    
    async def get_current_presence(self) -> Dict[str, Any]:
        """
        Get the current presence information.
        
        Returns:
            Dict containing the current presence information
        """
        active_sources = [s for s, v in self.presence_sources.items() if v]
        
        return {
            "location": self.current_location,
            "activity": self.current_activity,
            "active_sources": [s.name for s in active_sources],
            "last_update": {
                s.name: self.last_presence_update[s].isoformat()
                for s in active_sources
            }
        }
    
    # Notification Preference Methods
    
    async def set_notification_preference(
        self,
        message_type: str,
        preference: NotificationPreference
    ) -> None:
        """
        Set notification preference for a message type.
        
        Args:
            message_type: Type of message
            preference: Notification preference
        """
        self.notification_preferences[message_type] = preference
        await self.save_data()
    
    async def should_notify(
        self,
        message_type: str,
        priority: MessagePriority
    ) -> bool:
        """
        Determine if a notification should be sent based on current state.
        
        Args:
            message_type: Type of message
            priority: Message priority
            
        Returns:
            bool: True if notification should be sent, False otherwise
        """
        # Get current schedule and presence
        schedule = await self.get_current_schedule()
        presence = await self.get_current_presence()
        
        # Get notification preference
        preference = self.notification_preferences.get(
            message_type,
            NotificationPreference.WORKING_HOURS
        )
        
        # Always notify for high priority messages
        if priority == MessagePriority.URGENT or priority == MessagePriority.CRITICAL:
            return True
        
        # Check notification preference
        if preference == NotificationPreference.ALWAYS:
            return True
        elif preference == NotificationPreference.NEVER:
            return False
        elif preference == NotificationPreference.WORKING_HOURS:
            # Only notify during work hours
            return (
                schedule["activity"] == ActivityType.WORK and
                presence["location"] in [LocationType.LAB, LocationType.OFFICE]
            )
        elif preference == NotificationPreference.AWAKE:
            # Only notify when user is awake
            return (
                schedule["activity"] != ActivityType.SLEEP and
                presence["location"] != LocationType.BEDROOM
            )
        elif preference == NotificationPreference.HIGH_PRIORITY:
            # Only notify for high priority messages
            return priority == MessagePriority.HIGH
        
        # Default to not notifying
        return False
    
    # Background Tasks
    
    async def _periodic_save(self) -> None:
        """Periodically save data to disk"""
        while True:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                await self.save_data()
            except Exception as e:
                self.logger.error(f"Error in periodic save: {str(e)}")
                await asyncio.sleep(60)
    
    async def _check_schedule(self) -> None:
        """Periodically check schedule and update current activity"""
        while True:
            try:
                # Get current schedule
                schedule = await self.get_current_schedule()
                
                # Update current activity if not overridden by presence detection
                if len([s for s, v in self.presence_sources.items() if v]) < 2:
                    self.current_activity = schedule["activity"]
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error checking schedule: {str(e)}")
                await asyncio.sleep(60) 