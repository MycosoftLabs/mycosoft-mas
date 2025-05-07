"""
Message Types for Mycosoft MAS

This module defines the message types and related enums used in the Mycosoft MAS.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

class MessageType(Enum):
    """Types of messages in the system."""
    SYSTEM = "system"      # System-level messages
    AGENT = "agent"        # Inter-agent communication
    TASK = "task"          # Task-related messages
    DATA = "data"          # Data transfer messages
    SECURITY = "security"  # Security-related messages
    EVOLUTION = "evolution" # System evolution messages
    NOTIFICATION = "notification" # User notifications
    COMMUNICATION = "communication" # External communication

class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class MessageStatus(Enum):
    """Message status states."""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    PROCESSED = "processed"
    FAILED = "failed"
    EXPIRED = "expired"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"

@dataclass
class Message:
    """Base message class for all message types."""
    message_id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageType = MessageType.SYSTEM
    sender_id: str = ""
    recipient_id: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate the message."""
        # Check required fields
        if not all([self.message_id, self.message_type, self.sender_id, self.recipient_id]):
            return False
        
        # Check message type
        if not isinstance(self.message_type, MessageType):
            return False
        
        # Check timestamp
        if not isinstance(self.timestamp, datetime):
            return False
        
        # Check priority
        if not isinstance(self.priority, MessagePriority):
            return False
        
        # Check status
        if not isinstance(self.status, MessageStatus):
            return False
        
        # Check content
        if not isinstance(self.content, dict):
            return False
        
        # Check metadata
        if not isinstance(self.metadata, dict):
            return False
        
        # Check retry count
        if not isinstance(self.retry_count, int) or self.retry_count < 0:
            return False
        
        # Check max retries
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            return False
        
        # Check child message IDs
        if not isinstance(self.child_message_ids, list):
            return False
        
        return True

@dataclass
class SystemMessage(Message):
    """System-level messages."""
    def __post_init__(self):
        self.message_type = MessageType.SYSTEM
        self.priority = MessagePriority.HIGH

@dataclass
class AgentMessage(Message):
    """Inter-agent communication messages."""
    def __post_init__(self):
        self.message_type = MessageType.AGENT
        self.priority = MessagePriority.MEDIUM

@dataclass
class TaskMessage(Message):
    """Task-related messages."""
    def __post_init__(self):
        self.message_type = MessageType.TASK
        self.priority = MessagePriority.MEDIUM

@dataclass
class DataMessage(Message):
    """Data transfer messages."""
    def __post_init__(self):
        self.message_type = MessageType.DATA
        self.priority = MessagePriority.LOW

@dataclass
class SecurityMessage(Message):
    """Security-related messages."""
    def __post_init__(self):
        self.message_type = MessageType.SECURITY
        self.priority = MessagePriority.CRITICAL

@dataclass
class EvolutionMessage(Message):
    """System evolution messages."""
    def __post_init__(self):
        self.message_type = MessageType.EVOLUTION
        self.priority = MessagePriority.HIGH

@dataclass
class NotificationMessage(Message):
    """User notification messages."""
    def __post_init__(self):
        self.message_type = MessageType.NOTIFICATION
        self.priority = MessagePriority.MEDIUM

@dataclass
class CommunicationMessage(Message):
    """External communication messages."""
    def __post_init__(self):
        self.message_type = MessageType.COMMUNICATION
        self.priority = MessagePriority.MEDIUM

@dataclass
class FinancialMessage:
    """Message for financial operations"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: Dict[str, Any]
    financial_type: str
    financial_action: str
    financial_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list)

@dataclass
class PaymentMessage:
    """Message for payment processing"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: Dict[str, Any]
    payment_type: str
    payment_action: str
    payment_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list)

@dataclass
class SubscriptionMessage:
    """Message for subscription management"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: Dict[str, Any]
    subscription_type: str
    subscription_action: str
    subscription_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list)

@dataclass
class MonitoringMessage:
    """Message for system monitoring"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: Dict[str, Any]
    monitoring_type: str
    monitoring_action: str
    monitoring_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list)

@dataclass
class DashboardMessage:
    """Message for dashboard operations"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: Dict[str, Any]
    dashboard_type: str
    dashboard_action: str
    dashboard_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    child_message_ids: List[str] = field(default_factory=list) 