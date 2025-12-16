"""
Action Registry Module

Provides a registry for typed action definitions with metadata
about categories, risk levels, and approval requirements.
"""

import functools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ActionCategory(str, Enum):
    """Categories of actions for policy-based control."""
    # Read operations
    READ = "read"
    FILE_READ = "file_read"
    DATABASE_READ = "database_read"
    API_READ = "api_read"
    
    # Write operations
    WRITE = "write"
    FILE_WRITE = "file_write"
    DATABASE_WRITE = "database_write"
    API_WRITE = "api_write"
    
    # External operations
    EXTERNAL_READ = "external_read"
    EXTERNAL_WRITE = "external_write"
    
    # System operations
    SYSTEM_CONFIG = "system_config"
    SYSTEM_ADMIN = "system_admin"
    
    # Financial operations
    FINANCIAL = "financial"
    PAYMENT = "payment"
    
    # Data operations
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    
    # Communication
    EMAIL = "email"
    NOTIFICATION = "notification"
    
    # AI/LLM operations
    LLM_CALL = "llm_call"
    EMBEDDING = "embedding"
    
    # Agent operations
    AGENT_CONTROL = "agent_control"
    TASK_MANAGEMENT = "task_management"
    
    # Other
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionDefinition:
    """
    Definition of a registered action.
    
    Contains metadata about the action including category,
    risk level, and approval requirements.
    """
    name: str
    description: str
    category: ActionCategory
    risk_level: RiskLevel
    
    # Approval settings
    requires_approval: bool = False
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    timeout: int = 60  # seconds
    max_retries: int = 3
    
    # The actual function
    func: Optional[Callable] = None
    
    # Metadata
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"


class ActionRegistry:
    """
    Registry for typed action definitions.
    
    Provides a central place to register and look up actions
    with their metadata for policy enforcement.
    
    Usage:
        registry = ActionRegistry()
        
        # Register an action
        registry.register(
            name="send_email",
            description="Send an email",
            category=ActionCategory.EMAIL,
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
        )
        
        # Or use the decorator
        @registry.action(category=ActionCategory.EMAIL)
        async def send_email(to: str, subject: str):
            ...
    """
    
    _instance: Optional["ActionRegistry"] = None
    
    def __new__(cls) -> "ActionRegistry":
        """Singleton pattern for global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._actions = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._actions: dict[str, ActionDefinition] = {}
            self._initialized = True
    
    def register(
        self,
        name: str,
        description: str = "",
        category: ActionCategory = ActionCategory.OTHER,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        requires_approval: bool = False,
        auto_approve_conditions: Optional[dict[str, Any]] = None,
        timeout: int = 60,
        max_retries: int = 3,
        tags: Optional[list[str]] = None,
        func: Optional[Callable] = None,
    ) -> ActionDefinition:
        """
        Register an action definition.
        
        Args:
            name: Unique action name
            description: Human-readable description
            category: Action category for policy
            risk_level: Risk assessment
            requires_approval: Whether manual approval is required
            auto_approve_conditions: Conditions for automatic approval
            timeout: Execution timeout in seconds
            max_retries: Maximum retry attempts
            tags: Optional tags for filtering
            func: The action function
            
        Returns:
            The registered ActionDefinition
        """
        definition = ActionDefinition(
            name=name,
            description=description,
            category=category,
            risk_level=risk_level,
            requires_approval=requires_approval,
            auto_approve_conditions=auto_approve_conditions or {},
            timeout=timeout,
            max_retries=max_retries,
            tags=tags or [],
            func=func,
        )
        
        self._actions[name] = definition
        logger.debug(f"Registered action: {name} (category={category.value}, risk={risk_level.value})")
        
        return definition
    
    def get(self, name: str) -> Optional[ActionDefinition]:
        """Get an action definition by name."""
        return self._actions.get(name)
    
    def get_all(self) -> dict[str, ActionDefinition]:
        """Get all registered actions."""
        return self._actions.copy()
    
    def get_by_category(self, category: ActionCategory) -> list[ActionDefinition]:
        """Get all actions in a category."""
        return [a for a in self._actions.values() if a.category == category]
    
    def get_by_risk_level(self, risk_level: RiskLevel) -> list[ActionDefinition]:
        """Get all actions with a specific risk level."""
        return [a for a in self._actions.values() if a.risk_level == risk_level]
    
    def get_requiring_approval(self) -> list[ActionDefinition]:
        """Get all actions that require approval."""
        return [a for a in self._actions.values() if a.requires_approval]
    
    def action(
        self,
        name: Optional[str] = None,
        description: str = "",
        category: ActionCategory = ActionCategory.OTHER,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        requires_approval: bool = False,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """
        Decorator to register an action function.
        
        Usage:
            @registry.action(category=ActionCategory.EMAIL, risk_level=RiskLevel.HIGH)
            async def send_email(to: str, subject: str, body: str):
                ...
        """
        def decorator(func: F) -> F:
            action_name = name or func.__name__
            action_description = description or func.__doc__ or ""
            
            self.register(
                name=action_name,
                description=action_description,
                category=category,
                risk_level=risk_level,
                requires_approval=requires_approval,
                func=func,
                **kwargs,
            )
            
            @functools.wraps(func)
            def wrapper(*args: Any, **kw: Any) -> Any:
                return func(*args, **kw)
            
            return wrapper  # type: ignore
        
        return decorator
    
    def clear(self) -> None:
        """Clear all registered actions (useful for testing)."""
        self._actions.clear()


# Global registry instance
_registry: Optional[ActionRegistry] = None


def get_registry() -> ActionRegistry:
    """Get the global action registry."""
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry


def action(
    name: Optional[str] = None,
    description: str = "",
    category: ActionCategory = ActionCategory.OTHER,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    requires_approval: bool = False,
    **kwargs: Any,
) -> Callable[[F], F]:
    """
    Decorator to register an action with the global registry.
    
    Usage:
        @action(category="email", risk_level="high")
        async def send_email(to: str, subject: str):
            ...
    """
    return get_registry().action(
        name=name,
        description=description,
        category=category,
        risk_level=risk_level,
        requires_approval=requires_approval,
        **kwargs,
    )


# =============================================================================
# DEFAULT ACTION REGISTRATIONS
# =============================================================================

# These are registered automatically when the module is imported

def _register_default_actions() -> None:
    """Register common default actions."""
    registry = get_registry()
    
    # File operations
    registry.register(
        name="file_read",
        description="Read contents of a file",
        category=ActionCategory.FILE_READ,
        risk_level=RiskLevel.LOW,
    )
    
    registry.register(
        name="file_write",
        description="Write contents to a file",
        category=ActionCategory.FILE_WRITE,
        risk_level=RiskLevel.MEDIUM,
    )
    
    registry.register(
        name="file_delete",
        description="Delete a file",
        category=ActionCategory.DATA_DELETION,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )
    
    # Database operations
    registry.register(
        name="database_query",
        description="Execute a database query",
        category=ActionCategory.DATABASE_READ,
        risk_level=RiskLevel.LOW,
    )
    
    registry.register(
        name="database_write",
        description="Write data to database",
        category=ActionCategory.DATABASE_WRITE,
        risk_level=RiskLevel.MEDIUM,
    )
    
    registry.register(
        name="database_delete",
        description="Delete data from database",
        category=ActionCategory.DATA_DELETION,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )
    
    # External API operations
    registry.register(
        name="external_api_read",
        description="Read data from external API",
        category=ActionCategory.EXTERNAL_READ,
        risk_level=RiskLevel.LOW,
    )
    
    registry.register(
        name="external_api_write",
        description="Write data to external API",
        category=ActionCategory.EXTERNAL_WRITE,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )
    
    # Communication
    registry.register(
        name="send_email",
        description="Send an email",
        category=ActionCategory.EMAIL,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )
    
    registry.register(
        name="send_notification",
        description="Send a notification",
        category=ActionCategory.NOTIFICATION,
        risk_level=RiskLevel.LOW,
    )
    
    # LLM operations
    registry.register(
        name="llm_chat",
        description="Send chat completion request to LLM",
        category=ActionCategory.LLM_CALL,
        risk_level=RiskLevel.LOW,
    )
    
    registry.register(
        name="llm_embed",
        description="Generate embeddings",
        category=ActionCategory.EMBEDDING,
        risk_level=RiskLevel.LOW,
    )
    
    # Financial
    registry.register(
        name="process_payment",
        description="Process a financial payment",
        category=ActionCategory.PAYMENT,
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
    )
    
    # System
    registry.register(
        name="update_config",
        description="Update system configuration",
        category=ActionCategory.SYSTEM_CONFIG,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )


# Register defaults on module import
_register_default_actions()
