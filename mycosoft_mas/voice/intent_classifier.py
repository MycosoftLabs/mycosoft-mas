"""
Intent Classification Engine for MYCA Voice System
Created: February 4, 2026
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IntentPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class ConfirmationLevel(Enum):
    NONE = 0
    VERBAL = 1
    CHALLENGE = 2
    MFA = 3


@dataclass
class ExtractedEntity:
    entity_type: str
    value: str
    confidence: float
    position: Tuple[int, int]


@dataclass
class ClassifiedIntent:
    intent_category: str
    intent_action: str
    confidence: float
    entities: List[ExtractedEntity]
    priority: IntentPriority
    confirmation_level: ConfirmationLevel
    target_agents: List[str]
    fallback_agents: List[str]
    raw_transcript: str
    requires_context: bool = False
    context_keys: List[str] = field(default_factory=list)
    suggested_response: Optional[str] = None


INTENT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "agent_control": {
        "keywords": ["spawn", "start", "stop", "restart", "pause", "resume", "kill", "status", "list", "agents"],
        "patterns": [
            r"(?:spawn|start|create)\s+(?:an?\s+)?(?:new\s+)?(\w+)\s+agent",
            r"(?:stop|kill|terminate)\s+(?:the\s+)?(\w+)\s+agent",
        ],
        "agents": ["myca-orchestrator", "agent-manager", "health-monitor"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "learning": {
        "keywords": ["learn", "teach", "remember", "study", "research", "discover"],
        "patterns": [r"(?:learn|teach)\s+(?:how\s+to\s+)?(.+)"],
        "agents": ["skill-learning-agent", "research-agent", "memory-manager"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "coding": {
        "keywords": ["fix", "code", "create", "modify", "deploy", "merge", "pull request", "pr", "bug"],
        "patterns": [r"(?:fix|solve)\s+(?:the\s+)?(?:bug|issue)\s+(?:in|with)?\s*(.+)"],
        "agents": ["coding-agent", "github-agent", "deployment-agent"],
        "priority": IntentPriority.HIGH,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "business": {
        "keywords": ["report", "financial", "invoice", "contract", "revenue", "expense", "budget"],
        "patterns": [r"(?:show|get|generate)\s+(?:the\s+)?(?:financial|revenue)\s+report"],
        "agents": ["cfo-agent", "financial-agent", "accounting-agent"],
        "priority": IntentPriority.HIGH,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "infrastructure": {
        "keywords": ["server", "container", "docker", "network", "storage", "database", "proxmox", "vm"],
        "patterns": [r"(?:start|stop|restart)\s+(?:the\s+)?(\w+)\s+(?:server|container|vm)"],
        "agents": ["proxmox-agent", "docker-agent", "network-agent", "infrastructure-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "scientific": {
        "keywords": ["experiment", "analyze", "simulate", "mindex", "species", "fungal", "data"],
        "patterns": [r"(?:run|start)\s+(?:an?\s+)?experiment\s+(?:on|for)?\s*(.+)?"],
        "agents": ["mindex-agent", "research-agent", "simulation-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "security": {
        "keywords": ["threat", "incident", "audit", "scan", "security", "attack", "breach", "alert"],
        "patterns": [r"(?:run|start|perform)\s+(?:a\s+)?(?:security\s+)?scan"],
        "agents": ["security-agent", "watchdog-agent", "guardian-agent"],
        "priority": IntentPriority.CRITICAL,
        "confirmation": ConfirmationLevel.CHALLENGE,
    },
    "memory": {
        "keywords": ["remember", "recall", "forget", "context", "history", "conversation"],
        "patterns": [r"(?:remember|save)\s+(?:that\s+)?(.+)"],
        "agents": ["memory-manager", "context-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "communication": {
        "keywords": ["email", "message", "send", "notify", "call", "meeting", "calendar"],
        "patterns": [r"(?:send|write)\s+(?:an?\s+)?email\s+(?:to)?\s*(.+)"],
        "agents": ["secretary-agent", "email-agent", "calendar-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "device": {
        "keywords": ["device", "sensor", "mycobrain", "mushroom", "sporebase", "drone", "iot"],
        "patterns": [r"(?:show|get|check)\s+(?:the\s+)?(?:device|sensor)\s+(?:status|data)"],
        "agents": ["mycobrain-coordinator-agent", "device-manager-agent", "sensor-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "workflow": {
        "keywords": ["workflow", "automation", "n8n", "trigger", "run", "execute"],
        "patterns": [r"(?:run|execute|trigger)\s+(?:the\s+)?(\w+)\s+workflow"],
        "agents": ["n8n-agent", "workflow-generator-agent", "automation-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "system": {
        "keywords": ["system", "status", "health", "diagnostics", "performance", "metrics"],
        "patterns": [r"(?:show|get|check)\s+(?:the\s+)?system\s+(?:status|health)"],
        "agents": ["health-monitor", "diagnostics-agent", "metrics-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "ceo": {
        "keywords": ["approve", "authorize", "strategic", "decision", "company", "executive"],
        "patterns": [r"(?:approve|authorize)\s+(?:the\s+)?(.+)"],
        "agents": ["ceo-agent", "board-agent", "executive-agent"],
        "priority": IntentPriority.CRITICAL,
        "confirmation": ConfirmationLevel.MFA,
    },
    "dao": {
        "keywords": ["vote", "proposal", "governance", "dao", "treasury", "token", "stake"],
        "patterns": [r"(?:create|submit)\s+(?:a\s+)?proposal\s+(?:for)?\s*(.+)?"],
        "agents": ["dao-governance-agent", "dao-treasury-agent", "dao-voting-agent"],
        "priority": IntentPriority.HIGH,
        "confirmation": ConfirmationLevel.CHALLENGE,
    },
}

ENTITY_PATTERNS: Dict[str, str] = {
    "agent_name": r"(?:the\s+)?(\w+(?:-\w+)*)\s+agent",
    "number": r"\b(\d+(?:\.\d+)?)\b",
    "email": r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
}


class IntentClassifier:
    def __init__(self, custom_intents: Optional[Dict[str, Any]] = None):
        self.intents = INTENT_CATEGORIES.copy()
        if custom_intents:
            self.intents.update(custom_intents)
        self._compile_patterns()
        logger.info(f"IntentClassifier initialized with {len(self.intents)} categories")
    
    def _compile_patterns(self):
        self.compiled_patterns = {}
        for category, config in self.intents.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in config.get("patterns", [])
            ]
        self.compiled_entity_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in ENTITY_PATTERNS.items()
        }
    
    def classify(self, transcript: str) -> ClassifiedIntent:
        transcript = transcript.strip()
        transcript_lower = transcript.lower()
        
        scores: Dict[str, float] = {}
        for category, config in self.intents.items():
            score = 0.0
            keywords = config.get("keywords", [])
            keyword_matches = sum(1 for kw in keywords if kw in transcript_lower)
            if keywords:
                score += 0.3 * (keyword_matches / len(keywords))
            
            patterns = self.compiled_patterns.get(category, [])
            for pattern in patterns:
                if pattern.search(transcript_lower):
                    score += 0.7
                    break
            
            scores[category] = score
        
        # Guard against empty intents
        if not scores:
            best_category = "system"
            best_score = 0.0
        else:
            best_category = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_category]
        
        if best_score < 0.2:
            best_category = "system"
            best_score = 0.3
        
        # Validate category exists before accessing
        if best_category not in self.intents:
            best_category = "system"
            best_score = 0.3
        
        config = self.intents[best_category]
        entities = self._extract_entities(transcript)
        
        return ClassifiedIntent(
            intent_category=best_category,
            intent_action=self._extract_action(transcript_lower),
            confidence=min(best_score, 1.0),
            entities=entities,
            priority=config.get("priority", IntentPriority.MEDIUM),
            confirmation_level=config.get("confirmation", ConfirmationLevel.NONE),
            target_agents=config.get("agents", [])[:3],
            fallback_agents=config.get("agents", [])[3:],
            raw_transcript=transcript,
        )
    
    def _extract_action(self, transcript: str) -> str:
        action_verbs = {
            "create": ["create", "make", "build", "generate", "new"],
            "read": ["show", "get", "list", "display", "what", "check"],
            "update": ["update", "modify", "change", "edit", "set"],
            "delete": ["delete", "remove", "clear", "forget", "stop", "kill"],
            "execute": ["run", "execute", "trigger", "start", "perform", "do"],
        }
        for action, verbs in action_verbs.items():
            if any(verb in transcript for verb in verbs):
                return action
        return "process"
    
    def _extract_entities(self, transcript: str) -> List[ExtractedEntity]:
        entities = []
        for entity_type, pattern in self.compiled_entity_patterns.items():
            for match in pattern.finditer(transcript):
                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    value=match.group(1) if match.lastindex else match.group(0),
                    confidence=0.8,
                    position=(match.start(), match.end()),
                ))
        return entities


_classifier_instance: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


def classify_voice_command(transcript: str) -> ClassifiedIntent:
    return get_intent_classifier().classify(transcript)


__all__ = [
    "IntentClassifier", "ClassifiedIntent", "ExtractedEntity",
    "IntentPriority", "ConfirmationLevel", "get_intent_classifier",
    "classify_voice_command", "INTENT_CATEGORIES",
]
