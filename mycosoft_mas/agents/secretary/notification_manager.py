"""
Notification Manager for Secretary Agent

This module implements a notification manager that handles notifications based on
schedule and presence information, ensuring notifications are delivered at appropriate
times and through appropriate channels.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable, Awaitable
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass, field

from .schedule_manager import ScheduleManager, ActivityType, LocationType
from .presence_detector import PresenceDetector, DeviceType
from ..messaging.communication_service import CommunicationService

class NotificationType(Enum):
    """Types of notifications"""
    ALERT = auto()
    REMINDER = auto()
    UPDATE = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    CUSTOM = auto()

class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()
    URGENT = auto()

class NotificationChannel(Enum):
    """Available notification channels"""
    EMAIL = auto()
    TELEGRAM = auto()
    SIGNAL = auto()
    DISCORD = auto()
    VOICE = auto()
    TEXT = auto()
    PUSH = auto()
    CUSTOM = auto()

class NotificationStatus(Enum):
    """Status of a notification"""
    PENDING = auto()
    SCHEDULED = auto()
    DELIVERED = auto()
    READ = auto()
    FAILED = auto()
    CANCELLED = auto()
    EXPIRED = auto()

@dataclass
class Notification:
    """Information about a notification"""
    notification_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    channels: List[NotificationChannel]
    content: str
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    last_attempt: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

class NotificationManager:
    """
    Service that manages notifications based on schedule and presence.
    
    This class:
    1. Manages notification queues and delivery
    2. Integrates with schedule and presence information
    3. Handles notification preferences and rules
    4. Coordinates with the communication service
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        schedule_manager: ScheduleManager,
        presence_detector: PresenceDetector,
        communication_service: CommunicationService
    ):
        """
        Initialize the notification manager.
        
        Args:
            config: Configuration dictionary for the notification manager
            schedule_manager: Schedule manager instance
            presence_detector: Presence detector instance
            communication_service: Communication service instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.schedule_manager = schedule_manager
        self.presence_detector = presence_detector
        self.communication_service = communication_service
        
        # Create data directory
        self.data_dir = Path("data/secretary/notifications")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Notification queues
        self.notifications: Dict[str, Notification] = {}
        self.pending_queue: List[str] = []
        self.scheduled_queue: List[str] = []
        
        # Notification rules
        self.notification_rules: Dict[NotificationType, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            "notifications_created": 0,
            "notifications_delivered": 0,
            "notifications_failed": 0,
            "notifications_read": 0,
            "notifications_expired": 0,
            "average_delivery_time": 0.0
        }
        
        # Load data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load notification data from disk"""
        try:
            # Load notifications
            notifications_file = self.data_dir / "notifications.json"
            if notifications_file.exists():
                with open(notifications_file, "r") as f:
                    notifications_data = json.load(f)
                    
                    for notification_data in notifications_data:
                        notification = Notification(
                            notification_id=notification_data["notification_id"],
                            notification_type=NotificationType[notification_data["notification_type"]],
                            priority=NotificationPriority[notification_data["priority"]],
                            channels=[
                                NotificationChannel[c] for c in notification_data["channels"]
                            ],
                            content=notification_data["content"],
                            title=notification_data.get("title"),
                            created_at=datetime.fromisoformat(notification_data["created_at"]),
                            scheduled_for=datetime.fromisoformat(notification_data["scheduled_for"])
                                if notification_data.get("scheduled_for") else None,
                            expires_at=datetime.fromisoformat(notification_data["expires_at"])
                                if notification_data.get("expires_at") else None,
                            status=NotificationStatus[notification_data["status"]],
                            metadata=notification_data.get("metadata", {}),
                            retry_count=notification_data.get("retry_count", 0),
                            max_retries=notification_data.get("max_retries", 3),
                            last_attempt=datetime.fromisoformat(notification_data["last_attempt"])
                                if notification_data.get("last_attempt") else None,
                            delivered_at=datetime.fromisoformat(notification_data["delivered_at"])
                                if notification_data.get("delivered_at") else None,
                            read_at=datetime.fromisoformat(notification_data["read_at"])
                                if notification_data.get("read_at") else None
                        )
                        
                        self.notifications[notification.notification_id] = notification
                        
                        # Add to appropriate queue
                        if notification.status == NotificationStatus.PENDING:
                            self.pending_queue.append(notification.notification_id)
                        elif notification.status == NotificationStatus.SCHEDULED:
                            self.scheduled_queue.append(notification.notification_id)
            
            # Load notification rules
            rules_file = self.data_dir / "notification_rules.json"
            if rules_file.exists():
                with open(rules_file, "r") as f:
                    self.notification_rules = json.load(f)
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading notification data: {str(e)}")
    
    async def save_data(self) -> None:
        """Save notification data to disk"""
        try:
            # Save notifications
            notifications_file = self.data_dir / "notifications.json"
            notifications_data = []
            
            for notification in self.notifications.values():
                notification_data = {
                    "notification_id": notification.notification_id,
                    "notification_type": notification.notification_type.name,
                    "priority": notification.priority.name,
                    "channels": [c.name for c in notification.channels],
                    "content": notification.content,
                    "title": notification.title,
                    "created_at": notification.created_at.isoformat(),
                    "scheduled_for": notification.scheduled_for.isoformat()
                        if notification.scheduled_for else None,
                    "expires_at": notification.expires_at.isoformat()
                        if notification.expires_at else None,
                    "status": notification.status.name,
                    "metadata": notification.metadata,
                    "retry_count": notification.retry_count,
                    "max_retries": notification.max_retries,
                    "last_attempt": notification.last_attempt.isoformat()
                        if notification.last_attempt else None,
                    "delivered_at": notification.delivered_at.isoformat()
                        if notification.delivered_at else None,
                    "read_at": notification.read_at.isoformat()
                        if notification.read_at else None
                }
                notifications_data.append(notification_data)
            
            with open(notifications_file, "w") as f:
                json.dump(notifications_data, f, indent=2)
            
            # Save notification rules
            rules_file = self.data_dir / "notification_rules.json"
            with open(rules_file, "w") as f:
                json.dump(self.notification_rules, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving notification data: {str(e)}")
    
    async def start(self) -> None:
        """Start the notification manager"""
        self.logger.info("Starting notification manager")
        
        # Start background tasks
        asyncio.create_task(self._process_pending_queue())
        asyncio.create_task(self._check_scheduled_queue())
        asyncio.create_task(self._periodic_save())
        
        self.logger.info("Notification manager started")
    
    async def stop(self) -> None:
        """Stop the notification manager"""
        self.logger.info("Stopping notification manager")
        
        # Save data
        await self.save_data()
        
        self.logger.info("Notification manager stopped")
    
    # Notification Management Methods
    
    async def create_notification(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority,
        channels: List[NotificationChannel],
        content: str,
        title: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a new notification.
        
        Args:
            notification_type: Type of notification
            priority: Notification priority
            channels: Notification channels
            content: Notification content
            title: Notification title (optional)
            scheduled_for: When to send the notification (optional)
            expires_at: When the notification expires (optional)
            metadata: Additional notification data (optional)
            
        Returns:
            str: Notification ID
        """
        notification_id = str(uuid.uuid4())
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=notification_type,
            priority=priority,
            channels=channels,
            content=content,
            title=title,
            scheduled_for=scheduled_for,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.notifications[notification_id] = notification
        self.metrics["notifications_created"] += 1
        
        # Add to appropriate queue
        if scheduled_for:
            notification.status = NotificationStatus.SCHEDULED
            self.scheduled_queue.append(notification_id)
        else:
            self.pending_queue.append(notification_id)
        
        await self.save_data()
        
        return notification_id
    
    async def cancel_notification(self, notification_id: str) -> None:
        """
        Cancel a notification.
        
        Args:
            notification_id: Notification ID
        """
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            notification.status = NotificationStatus.CANCELLED
            
            # Remove from queues
            if notification_id in self.pending_queue:
                self.pending_queue.remove(notification_id)
            if notification_id in self.scheduled_queue:
                self.scheduled_queue.remove(notification_id)
            
            await self.save_data()
    
    async def mark_notification_read(self, notification_id: str) -> None:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
        """
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now()
            
            self.metrics["notifications_read"] += 1
            
            await self.save_data()
    
    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get notification information.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            Optional[Notification]: Notification information, or None if not found
        """
        return self.notifications.get(notification_id)
    
    async def get_pending_notifications(self) -> List[Notification]:
        """
        Get all pending notifications.
        
        Returns:
            List[Notification]: List of pending notifications
        """
        return [
            self.notifications[notification_id]
            for notification_id in self.pending_queue
        ]
    
    async def get_scheduled_notifications(self) -> List[Notification]:
        """
        Get all scheduled notifications.
        
        Returns:
            List[Notification]: List of scheduled notifications
        """
        return [
            self.notifications[notification_id]
            for notification_id in self.scheduled_queue
        ]
    
    # Notification Rules
    
    async def add_notification_rule(
        self,
        notification_type: NotificationType,
        rule: Dict[str, Any]
    ) -> None:
        """
        Add a notification rule.
        
        Args:
            notification_type: Type of notification
            rule: Rule configuration
        """
        self.notification_rules[notification_type] = rule
        await self.save_data()
    
    async def remove_notification_rule(self, notification_type: NotificationType) -> None:
        """
        Remove a notification rule.
        
        Args:
            notification_type: Type of notification
        """
        if notification_type in self.notification_rules:
            del self.notification_rules[notification_type]
            await self.save_data()
    
    async def get_notification_rule(
        self,
        notification_type: NotificationType
    ) -> Optional[Dict[str, Any]]:
        """
        Get a notification rule.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            Optional[Dict[str, Any]]: Rule configuration, or None if not found
        """
        return self.notification_rules.get(notification_type)
    
    # Notification Delivery
    
    async def _should_deliver_notification(
        self,
        notification: Notification
    ) -> bool:
        """
        Check if a notification should be delivered based on schedule and presence.
        
        Args:
            notification: Notification to check
            
        Returns:
            bool: True if the notification should be delivered
        """
        try:
            # Check if notification is expired
            if notification.expires_at and datetime.now() > notification.expires_at:
                notification.status = NotificationStatus.EXPIRED
                self.metrics["notifications_expired"] += 1
                await self.save_data()
                return False
            
            # Get current schedule and presence
            current_schedule = await self.schedule_manager.get_current_schedule()
            current_presence = await self.schedule_manager.get_current_presence()
            
            # Get notification rule
            rule = await self.get_notification_rule(notification.notification_type)
            if not rule:
                return True
            
            # Check schedule rules
            if "schedule_rules" in rule:
                schedule_rules = rule["schedule_rules"]
                
                # Check if current activity is in blocked activities
                if "blocked_activities" in schedule_rules:
                    if current_schedule and current_schedule.activity in schedule_rules["blocked_activities"]:
                        return False
                
                # Check if current location is in blocked locations
                if "blocked_locations" in schedule_rules:
                    if current_presence and current_presence.location in schedule_rules["blocked_locations"]:
                        return False
            
            # Check presence rules
            if "presence_rules" in rule:
                presence_rules = rule["presence_rules"]
                
                # Check if presence is required
                if presence_rules.get("require_presence", False):
                    if not current_presence:
                        return False
                
                # Check if specific presence source is required
                if "required_sources" in presence_rules:
                    if not current_presence or current_presence.source not in presence_rules["required_sources"]:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking notification delivery: {str(e)}")
            return False
    
    async def _deliver_notification(self, notification: Notification) -> bool:
        """
        Deliver a notification through the specified channels.
        
        Args:
            notification: Notification to deliver
            
        Returns:
            bool: True if delivery was successful
        """
        try:
            # Check if notification should be delivered
            if not await self._should_deliver_notification(notification):
                return False
            
            # Update notification status
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now()
            notification.last_attempt = datetime.now()
            
            # Deliver through each channel
            for channel in notification.channels:
                try:
                    if channel == NotificationChannel.EMAIL:
                        await self.communication_service.send_email(
                            notification.content,
                            notification.title
                        )
                    elif channel == NotificationChannel.TELEGRAM:
                        await self.communication_service.send_telegram(
                            notification.content
                        )
                    elif channel == NotificationChannel.SIGNAL:
                        await self.communication_service.send_signal(
                            notification.content
                        )
                    elif channel == NotificationChannel.DISCORD:
                        await self.communication_service.send_discord(
                            notification.content
                        )
                    elif channel == NotificationChannel.VOICE:
                        await self.communication_service.send_voice(
                            notification.content
                        )
                    elif channel == NotificationChannel.TEXT:
                        await self.communication_service.send_text(
                            notification.content
                        )
                    elif channel == NotificationChannel.PUSH:
                        await self.communication_service.send_push(
                            notification.content,
                            notification.title
                        )
                except Exception as e:
                    self.logger.error(f"Error delivering notification through {channel.name}: {str(e)}")
                    notification.retry_count += 1
                    
                    if notification.retry_count >= notification.max_retries:
                        notification.status = NotificationStatus.FAILED
                        self.metrics["notifications_failed"] += 1
                        await self.save_data()
                        return False
            
            # Update metrics
            self.metrics["notifications_delivered"] += 1
            
            # Calculate average delivery time
            delivery_time = (notification.delivered_at - notification.created_at).total_seconds()
            self.metrics["average_delivery_time"] = (
                (self.metrics["average_delivery_time"] * (self.metrics["notifications_delivered"] - 1) + delivery_time)
                / self.metrics["notifications_delivered"]
            )
            
            await self.save_data()
            return True
            
        except Exception as e:
            self.logger.error(f"Error delivering notification: {str(e)}")
            notification.status = NotificationStatus.FAILED
            self.metrics["notifications_failed"] += 1
            await self.save_data()
            return False
    
    # Background Tasks
    
    async def _process_pending_queue(self) -> None:
        """Process the pending notification queue"""
        while True:
            try:
                # Process each pending notification
                for notification_id in self.pending_queue[:]:
                    notification = self.notifications[notification_id]
                    
                    # Try to deliver the notification
                    if await self._deliver_notification(notification):
                        # Remove from pending queue if successful
                        self.pending_queue.remove(notification_id)
                    else:
                        # Move to end of queue if failed
                        self.pending_queue.remove(notification_id)
                        self.pending_queue.append(notification_id)
                
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Error processing pending queue: {str(e)}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_queue(self) -> None:
        """Check the scheduled notification queue"""
        while True:
            try:
                now = datetime.now()
                
                # Check each scheduled notification
                for notification_id in self.scheduled_queue[:]:
                    notification = self.notifications[notification_id]
                    
                    # Check if it's time to deliver
                    if notification.scheduled_for and now >= notification.scheduled_for:
                        # Move to pending queue
                        self.scheduled_queue.remove(notification_id)
                        self.pending_queue.append(notification_id)
                        notification.status = NotificationStatus.PENDING
                
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Error checking scheduled queue: {str(e)}")
                await asyncio.sleep(60)
    
    async def _periodic_save(self) -> None:
        """Periodically save data to disk"""
        while True:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                await self.save_data()
            except Exception as e:
                self.logger.error(f"Error in periodic save: {str(e)}")
                await asyncio.sleep(60) 