from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DEPENDENCY_REQUEST = "dependency_request"
    INTEGRATION_REQUEST = "integration_request"
    TASK_REQUEST = "task_request"
    HEALTH_CHECK = "health_check"
    SECURITY_ALERT = "security_alert"
    MONITORING_UPDATE = "monitoring_update"
    TECHNOLOGY_UPDATE = "technology_update"
    EVOLUTION_ALERT = "evolution_alert"
    SYSTEM_UPDATE = "system_update"

class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Message:
    """Base message class for agent communication."""
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = datetime.now()
    priority: MessagePriority = MessagePriority.MEDIUM
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary format."""
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            message_type=MessageType(data["message_type"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=MessagePriority(data["priority"]),
            metadata=data.get("metadata")
        )

@dataclass
class TaskMessage(Message):
    """Message for task assignments between agents."""
    def __init__(
        self,
        message_id: str,
        sender_id: str,
        recipient_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        content = {
            "task_type": task_type,
            "task_data": task_data
        }
        super().__init__(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.TASK_REQUEST,
            content=content,
            priority=priority,
            metadata=metadata
        )

@dataclass
class NotificationMessage(Message):
    """Message for notifications between agents."""
    def __init__(
        self,
        message_id: str,
        sender_id: str,
        recipient_id: str,
        notification_type: str,
        notification_data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        content = {
            "notification_type": notification_type,
            "notification_data": notification_data
        }
        super().__init__(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.NOTIFICATION,
            content=content,
            priority=priority,
            metadata=metadata
        )

@dataclass
class ErrorMessage(Message):
    """Message for error reporting between agents."""
    def __init__(
        self,
        message_id: str,
        sender_id: str,
        recipient_id: str,
        error_type: str,
        error_data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
        metadata: Optional[Dict[str, Any]] = None
    ):
        content = {
            "error_type": error_type,
            "error_data": error_data
        }
        super().__init__(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.ERROR,
            content=content,
            priority=priority,
            metadata=metadata
        )

def create_dependency_request(
    sender: str,
    receiver: str,
    action: str,
    package: str,
    version: Optional[str] = None,
    token: Optional[str] = None
) -> 'Message':
    """Create a dependency request message."""
    content = {
        "action": action,
        "package": package
    }
    if version:
        content["version"] = version
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.DEPENDENCY_REQUEST,
        content=content,
        timestamp=datetime.now(),
        priority=MessagePriority.MEDIUM,
        metadata={"token": token}
    )

def create_integration_request(
    sender: str,
    receiver: str,
    action: str,
    integration_id: str,
    config: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None
) -> 'Message':
    """Create an integration request message."""
    content = {
        "action": action,
        "integration_id": integration_id
    }
    if config:
        content["config"] = config
    if data:
        content["data"] = data
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.INTEGRATION_REQUEST,
        content=content,
        timestamp=datetime.now(),
        priority=MessagePriority.MEDIUM,
        metadata={"token": token}
    )

def create_task_request(
    sender: str,
    receiver: str,
    action: str,
    task: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    token: Optional[str] = None
) -> 'Message':
    """Create a task request message."""
    content = {"action": action}
    if task:
        content["task"] = task
    if task_id:
        content["task_id"] = task_id
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.TASK_REQUEST,
        content=content,
        timestamp=datetime.now(),
        priority=MessagePriority.MEDIUM,
        metadata={"token": token}
    )

def create_health_check(
    sender: str,
    receiver: str,
    token: Optional[str] = None
) -> 'Message':
    """Create a health check message."""
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.HEALTH_CHECK,
        content={},
        timestamp=datetime.now(),
        priority=MessagePriority.MEDIUM,
        metadata={"token": token}
    )

def create_security_alert(
    sender: str,
    receiver: str,
    alert_type: str,
    message: str,
    severity: str,
    token: Optional[str] = None
) -> 'Message':
    """Create a security alert message."""
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.SECURITY_ALERT,
        content={
            "alert_type": alert_type,
            "message": message,
            "severity": severity
        },
        timestamp=datetime.now(),
        priority=MessagePriority.HIGH,
        metadata={"token": token}
    )

def create_monitoring_update(
    sender: str,
    receiver: str,
    metrics: Dict[str, Any],
    token: Optional[str] = None
) -> 'Message':
    """Create a monitoring update message."""
    return Message(
        message_id="",
        sender_id=sender,
        recipient_id=receiver,
        message_type=MessageType.MONITORING_UPDATE,
        content={"metrics": metrics},
        timestamp=datetime.now(),
        priority=MessagePriority.MEDIUM,
        metadata={"token": token}
    )

def create_technology_update(
    sender: str,
    receiver: str,
    technology: Dict[str, Any],
    token: Optional[str] = None
) -> 'Message':
    """Create a technology update message."""
    return Message(
        type=MessageType.TECHNOLOGY_UPDATE,
        sender=sender,
        receiver=receiver,
        content={
            "technology": technology,
            "timestamp": datetime.now().isoformat()
        },
        token=token
    )

def create_evolution_alert(
    sender: str,
    receiver: str,
    alert_type: str,
    message: str,
    severity: str,
    token: Optional[str] = None
) -> 'Message':
    """Create an evolution alert message."""
    return Message(
        type=MessageType.EVOLUTION_ALERT,
        sender=sender,
        receiver=receiver,
        content={
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        },
        token=token
    )

def create_system_update(
    sender: str,
    receiver: str,
    update_type: str,
    details: Dict[str, Any],
    token: Optional[str] = None
) -> 'Message':
    """Create a system update message."""
    return Message(
        type=MessageType.SYSTEM_UPDATE,
        sender=sender,
        receiver=receiver,
        content={
            "update_type": update_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        },
        token=token
    ) 