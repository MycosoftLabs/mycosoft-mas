"""
Voice Command Registry for MYCA
Created: February 4, 2026
"""

import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CommandType(Enum):
    AGENT = "agent"
    WORKFLOW = "workflow"
    SYSTEM = "system"
    NAVIGATION = "navigation"
    QUERY = "query"


class ExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"


@dataclass
class CommandHandler:
    handler_type: str
    handler_id: str
    endpoint: Optional[str] = None
    method: Optional[str] = None


@dataclass
class CommandMatch:
    command_id: str
    confidence: float
    matched_pattern: str
    captured_groups: Dict[str, str]


@dataclass
class RegisteredCommand:
    command_id: str
    name: str
    description: str
    patterns: List[str]
    command_type: CommandType
    handler: CommandHandler
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    requires_confirmation: bool = False
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    enabled: bool = True
    usage_count: int = 0
    last_used: Optional[datetime] = None


class VoiceCommandRegistry:
    def __init__(self):
        self.commands: Dict[str, RegisteredCommand] = {}
        self._compiled: Dict[str, List[re.Pattern]] = {}
        self._load_default_commands()
        logger.info(f"VoiceCommandRegistry initialized with {len(self.commands)} commands")
    
    def _load_default_commands(self):
        defaults = [
            RegisteredCommand(
                command_id="agent_status",
                name="Get Agent Status",
                description="Show the status of all running agents",
                patterns=[r"(?:show|get|list)\s+(?:all\s+)?agent\s*(?:status)?"],
                command_type=CommandType.AGENT,
                handler=CommandHandler("agent", "agent-manager", "/api/agents/status", "GET"),
                examples=["show agent status", "list all agents"],
            ),
            RegisteredCommand(
                command_id="spawn_agent",
                name="Spawn Agent",
                description="Create a new agent instance",
                patterns=[r"(?:spawn|start|create)\s+(?:a\s+)?new\s+(\w+)\s+agent"],
                command_type=CommandType.AGENT,
                handler=CommandHandler("agent", "agent-manager", "/api/agents/spawn", "POST"),
                requires_confirmation=True,
                examples=["spawn a new research agent", "create new security agent"],
            ),
            RegisteredCommand(
                command_id="run_workflow",
                name="Run Workflow",
                description="Execute an n8n workflow",
                patterns=[r"(?:run|execute|trigger)\s+(?:the\s+)?(\w+)\s+workflow"],
                command_type=CommandType.WORKFLOW,
                handler=CommandHandler("workflow", "n8n-client", "/api/workflows/execute", "POST"),
                examples=["run the backup workflow", "trigger security workflow"],
            ),
            RegisteredCommand(
                command_id="system_health",
                name="System Health Check",
                description="Get system health status",
                patterns=[r"(?:check|show|get)\s+system\s+(?:health|status)"],
                command_type=CommandType.SYSTEM,
                handler=CommandHandler("system", "health-monitor", "/api/health", "GET"),
                examples=["check system health", "show system status"],
            ),
            RegisteredCommand(
                command_id="learn_skill",
                name="Learn New Skill",
                description="Learn a new capability via LLM",
                patterns=[r"learn\s+(?:how\s+to\s+)?(.+)"],
                command_type=CommandType.AGENT,
                handler=CommandHandler("agent", "skill-learning-agent", "/api/skills/learn", "POST"),
                examples=["learn how to optimize containers", "learn kubernetes deployments"],
            ),
            RegisteredCommand(
                command_id="fix_bug",
                name="Fix Bug",
                description="Analyze and fix a code bug",
                patterns=[r"fix\s+(?:the\s+)?(?:bug|issue)\s+(?:in|with|on)?\s*(.+)"],
                command_type=CommandType.AGENT,
                handler=CommandHandler("agent", "coding-agent", "/api/code/fix", "POST"),
                requires_confirmation=True,
                examples=["fix the bug in the API", "fix issue with login"],
            ),
            RegisteredCommand(
                command_id="remember",
                name="Remember Information",
                description="Store information in memory",
                patterns=[r"(?:remember|save)\s+(?:that\s+)?(.+)"],
                command_type=CommandType.SYSTEM,
                handler=CommandHandler("system", "memory-manager", "/api/memory/store", "POST"),
                examples=["remember that John prefers dark mode", "save API key location"],
            ),
            RegisteredCommand(
                command_id="recall",
                name="Recall Information",
                description="Retrieve information from memory",
                patterns=[r"(?:recall|what)\s+(?:is|did|was|about)\s+(.+)"],
                command_type=CommandType.QUERY,
                handler=CommandHandler("system", "memory-manager", "/api/memory/recall", "GET"),
                examples=["what is the database password", "recall server configuration"],
            ),
            RegisteredCommand(
                command_id="navigate_dashboard",
                name="Navigate Dashboard",
                description="Navigate to a dashboard page",
                patterns=[r"(?:go\s+to|open|navigate\s+to)\s+(?:the\s+)?(\w+)\s*(?:dashboard|page)?"],
                command_type=CommandType.NAVIGATION,
                handler=CommandHandler("navigation", "frontend-router"),
                examples=["go to the MINDEX dashboard", "open settings page"],
            ),
            # NatureOS MATLAB-driven analyses (PersonaPlex voice commands)
            RegisteredCommand(
                command_id="natureos.analyze_zone",
                name="Analyze Zone",
                description="Analyze soil quality or telemetry in a zone",
                patterns=[
                    r"analyze\s+(?:soil\s+quality|telemetry)\s+in\s+zone\s+([A-Za-z0-9]+)",
                    r"analyze\s+zone\s+([A-Za-z0-9]+)",
                ],
                command_type=CommandType.QUERY,
                handler=CommandHandler("natureos", "natureos-matlab", "/api/voice/tools/execute", "POST"),
                examples=["analyze soil quality in zone A", "analyze zone B"],
            ),
            RegisteredCommand(
                command_id="natureos.forecast",
                name="Environmental Forecast",
                description="Predict temperature or humidity for next hours",
                patterns=[
                    r"predict\s+(?:temperature|humidity)\s+for\s+(?:the\s+)?next\s+(\d+)\s*hours?",
                    r"forecast\s+(?:temperature|humidity)\s+(?:for\s+)?(\d+)\s*hours?",
                ],
                command_type=CommandType.QUERY,
                handler=CommandHandler("natureos", "natureos-matlab", "/api/voice/tools/execute", "POST"),
                examples=["predict temperature for next 24 hours", "forecast humidity 12 hours"],
            ),
            RegisteredCommand(
                command_id="natureos.anomaly_scan",
                name="Sensor Anomaly Scan",
                description="Check for sensor anomalies",
                patterns=[
                    r"(?:are\s+there\s+any\s+)?sensor\s+anomalies?",
                    r"check\s+for\s+anomalies",
                    r"run\s+anomaly\s+(?:scan|detection)",
                ],
                command_type=CommandType.QUERY,
                handler=CommandHandler("natureos", "natureos-matlab", "/api/voice/tools/execute", "POST"),
                examples=["are there any sensor anomalies?", "check for anomalies"],
            ),
            RegisteredCommand(
                command_id="natureos.classify",
                name="Identify Fungal Sample",
                description="Identify fungal sample from morphology",
                patterns=[
                    r"identify\s+(?:this\s+)?fungal\s+sample",
                    r"classify\s+(?:this\s+)?(?:fungal|mushroom)\s+sample",
                ],
                command_type=CommandType.QUERY,
                handler=CommandHandler("natureos", "natureos-matlab", "/api/voice/tools/execute", "POST"),
                examples=["identify this fungal sample"],
            ),
            RegisteredCommand(
                command_id="natureos.biodiversity_report",
                name="Biodiversity Report",
                description="Generate biodiversity report",
                patterns=[
                    r"generate\s+biodiversity\s+report",
                    r"(?:create|run)\s+biodiversity\s+report",
                ],
                command_type=CommandType.QUERY,
                handler=CommandHandler("natureos", "natureos-matlab", "/api/voice/tools/execute", "POST"),
                examples=["generate biodiversity report"],
            ),
        ]
        
        for cmd in defaults:
            self.register(cmd)
    
    def register(self, command: RegisteredCommand) -> None:
        self.commands[command.command_id] = command
        self._compiled[command.command_id] = [
            re.compile(p, re.IGNORECASE) for p in command.patterns
        ]
        logger.debug(f"Registered command: {command.command_id}")
    
    def unregister(self, command_id: str) -> bool:
        if command_id in self.commands:
            del self.commands[command_id]
            del self._compiled[command_id]
            return True
        return False
    
    def match(self, transcript: str) -> Optional[CommandMatch]:
        best_match = None
        best_score = 0.0
        
        for cmd_id, patterns in self._compiled.items():
            cmd = self.commands[cmd_id]
            if not cmd.enabled:
                continue
            
            for pattern in patterns:
                m = pattern.search(transcript)
                if m:
                    score = len(m.group(0)) / len(transcript) if transcript else 0
                    if score > best_score:
                        best_score = score
                        groups = m.groupdict() if m.groupdict() else {}
                        if m.lastindex:
                            for i in range(1, m.lastindex + 1):
                                groups[f"group{i}"] = m.group(i)
                        best_match = CommandMatch(
                            command_id=cmd_id,
                            confidence=min(score + 0.3, 1.0),
                            matched_pattern=pattern.pattern,
                            captured_groups=groups,
                        )
        
        return best_match
    
    def get_command(self, command_id: str) -> Optional[RegisteredCommand]:
        return self.commands.get(command_id)
    
    def record_usage(self, command_id: str) -> None:
        if cmd := self.commands.get(command_id):
            cmd.usage_count += 1
            cmd.last_used = datetime.now()
    
    def get_suggestions(self, partial: str, limit: int = 5) -> List[RegisteredCommand]:
        partial_lower = partial.lower()
        scored = []
        for cmd in self.commands.values():
            if not cmd.enabled:
                continue
            score = 0
            if partial_lower in cmd.name.lower():
                score += 2
            for alias in cmd.aliases:
                if partial_lower in alias.lower():
                    score += 1
            for example in cmd.examples:
                if partial_lower in example.lower():
                    score += 0.5
            if score > 0:
                scored.append((score, cmd))
        scored.sort(key=lambda x: (-x[0], -x[1].usage_count))
        return [cmd for _, cmd in scored[:limit]]


_registry_instance: Optional[VoiceCommandRegistry] = None


def get_command_registry() -> VoiceCommandRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = VoiceCommandRegistry()
    return _registry_instance


__all__ = [
    "VoiceCommandRegistry", "RegisteredCommand", "CommandHandler",
    "CommandMatch", "CommandType", "ExecutionMode", "get_command_registry",
]
