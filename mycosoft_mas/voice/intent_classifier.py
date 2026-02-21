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
    "greeting": {
        "keywords": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy"],
        "patterns": [
            r"^(?:hello|hi|hey|greetings|howdy)(?:\s+myca|\s+there)?",
            r"^good\s+(?:morning|afternoon|evening|day)",
        ],
        "agents": ["conversation-agent", "secretary-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "question": {
        "keywords": ["what", "how", "why", "when", "where", "who", "which", "can you", "could you", "would you"],
        "patterns": [
            r"^(?:what|how|why|when|where|who|which)\s+",
            r"^(?:can|could|would)\s+you\s+",
            r"^(?:is|are|do|does)\s+",
        ],
        "agents": ["research-agent", "mindex-agent", "memory-manager"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "command": {
        "keywords": ["do", "start", "stop", "create", "make", "build", "run", "execute", "launch", "kill", "terminate"],
        "patterns": [
            r"(?:start|stop|restart|pause|resume)\s+",
            r"(?:create|make|build|generate)\s+(?:a|an|the)?\s*",
            r"(?:run|execute|launch|trigger)\s+",
            r"(?:kill|terminate|end)\s+",
        ],
        "agents": ["orchestrator", "agent-manager", "executor-agent"],
        "priority": IntentPriority.HIGH,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "search": {
        "keywords": ["find", "search", "look up", "lookup", "query", "locate", "discover"],
        "patterns": [
            r"(?:find|search|look\s+up|lookup)\s+(?:for\s+)?",
            r"(?:locate|discover)\s+",
            r"query\s+(?:for\s+)?",
        ],
        "agents": ["mindex-agent", "search-agent", "research-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "navigation": {
        "keywords": ["go to", "open", "show", "display", "navigate", "view", "switch to"],
        "patterns": [
            r"(?:go\s+to|navigate\s+to)\s+",
            r"(?:open|show|display)\s+(?:the\s+)?",
            r"(?:switch\s+to|view)\s+",
        ],
        "agents": ["ui-agent", "navigation-agent", "website-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "device_control": {
        "keywords": ["turn on", "turn off", "set", "configure", "adjust", "control", "device", "sensor"],
        "patterns": [
            r"(?:turn\s+(?:on|off)|switch\s+(?:on|off))\s+(?:the\s+)?",
            r"(?:set|configure|adjust)\s+(?:the\s+)?",
            r"(?:control|manage)\s+(?:the\s+)?(?:device|sensor)",
        ],
        "agents": ["mycobrain-coordinator-agent", "device-manager-agent", "iot-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "experiment": {
        "keywords": ["experiment", "test", "hypothesis", "trial", "lab", "analyze", "measure"],
        "patterns": [
            r"(?:run|start|begin)\s+(?:an?\s+)?experiment",
            r"(?:test|verify)\s+(?:the\s+)?hypothesis",
            r"(?:conduct|perform)\s+(?:a\s+)?(?:trial|test)",
        ],
        "agents": ["lab-agent", "research-agent", "hypothesis-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "workflow": {
        "keywords": ["workflow", "automation", "n8n", "pipeline", "automate"],
        "patterns": [
            r"(?:create|build|make)\s+(?:a\s+)?workflow",
            r"(?:run|execute|trigger)\s+(?:the\s+)?(?:\w+\s+)?workflow",
            r"(?:start|launch|run)\s+(?:the\s+)?automation",
            r"trigger\s+(?:the\s+)?",
        ],
        "agents": ["n8n-agent", "workflow-generator-agent", "automation-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "memory": {
        "keywords": ["remember", "recall", "forget", "context", "history", "conversation", "note"],
        "patterns": [
            r"(?:remember|save|store)\s+(?:that\s+)?",
            r"(?:recall|retrieve|get)\s+(?:the\s+)?(?:context|history|conversation)",
            r"(?:forget|delete|remove)\s+(?:about\s+)?",
        ],
        "agents": ["memory-manager", "context-agent", "history-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "status": {
        "keywords": ["status", "health", "diagnostics", "metrics", "uptime", "monitoring"],
        "patterns": [
            r"(?:check|show|get)\s+(?:the\s+)?status",
            r"(?:health|diagnostics)\s+(?:check|report)",
            r"(?:show|display|get)\s+(?:the\s+)?(?:metrics|performance)",
            r"(?:check|monitor)\s+(?:system\s+)?(?:health|performance)",
        ],
        "agents": ["health-monitor", "diagnostics-agent", "metrics-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
    "deploy": {
        "keywords": ["deploy", "deployment", "release", "publish", "docker", "container", "server restart"],
        "patterns": [
            r"(?:deploy|push)\s+(?:to\s+)?",
            r"(?:build|rebuild)\s+(?:the\s+)?(?:docker|image|container)",
            r"(?:restart|reload)\s+(?:the\s+)?(?:service|server|container|application)",
            r"(?:release|publish)\s+",
        ],
        "agents": ["deployment-agent", "github-agent", "docker-agent"],
        "priority": IntentPriority.HIGH,
        "confirmation": ConfirmationLevel.VERBAL,
    },
    "security": {
        "keywords": ["audit", "security", "threat", "vulnerability", "breach", "penetration test"],
        "patterns": [
            r"(?:run|start|perform)\s+(?:a\s+)?(?:security\s+)?(?:audit|scan)",
            r"(?:check|verify)\s+security",
            r"(?:detect|find)\s+(?:threats|vulnerabilities)",
            r"scan\s+(?:for\s+)?(?:vulnerabilities|threats|security)",
        ],
        "agents": ["security-agent", "guardian-agent", "watchdog-agent"],
        "priority": IntentPriority.CRITICAL,
        "confirmation": ConfirmationLevel.CHALLENGE,
    },
    "scientific": {
        "keywords": ["simulation", "compute", "model", "calculate", "scientific"],
        "patterns": [
            r"(?:run|start)\s+(?:a\s+)?simulation",
            r"(?:analyze|process)\s+(?:the\s+)?(?:scientific\s+)?data",
            r"(?:compute|calculate)\s+",
            r"lab\s+(?:monitoring|report|status|data)",
        ],
        "agents": ["simulation-agent", "lab-agent", "compute-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "natureos": {
        "keywords": [
            "analyze", "zone", "soil", "forecast", "temperature", "humidity",
            "anomaly", "anomalies", "sensor", "identify", "fungal", "biodiversity",
            "earth2", "earth-2", "earth forecast", "simulation", "petri",
            "mushroom", "compound", "genetic circuit", "lifecycle", "physics",
            "growth analytics", "retrosynthesis", "alchemy", "digital twin",
            "symbiosis", "spore", "spores", "dispersal",
        ],
        "patterns": [
            r"analyze\s+(?:soil\s+quality|zone|telemetry)",
            r"predict\s+(?:temperature|humidity)",
            r"(?:are\s+there\s+any\s+)?sensor\s+anomalies",
            r"identify\s+(?:this\s+)?fungal\s+sample",
            r"generate\s+biodiversity\s+report",
            r"(?:run|start)\s+earth\s*2\s+forecast",
            r"(?:run|simulate)\s+(?:a\s+)?petri\s+dish",
            r"(?:run|simulate)\s+mushroom",
            r"(?:run|simulate)\s+compound",
            r"(?:run|simulate)\s+genetic\s+circuit",
            r"(?:run|simulate)\s+lifecycle",
            r"(?:run|simulate)\s+physics",
            r"growth\s+analytics",
            r"retrosynthesis",
            r"alchemy\s+lab",
            r"sync\s+(?:the\s+)?digital\s+twin",
            r"symbiosis\s+network",
            r"(?:track|analyze)\s+spores",
        ],
        "agents": ["natureos-matlab", "lab-agent", "simulation-agent"],
        "priority": IntentPriority.MEDIUM,
        "confirmation": ConfirmationLevel.NONE,
    },
    "general": {
        "keywords": [],  # Fallback category - matches nothing specifically
        "patterns": [],
        "agents": ["orchestrator", "secretary-agent"],
        "priority": IntentPriority.LOW,
        "confirmation": ConfirmationLevel.NONE,
    },
}

ENTITY_PATTERNS: Dict[str, str] = {
    "agent_name": r"(?:the\s+)?(\w+(?:-\w+)*-agent)\b",
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
            best_category = "general"
            best_score = 0.3
        else:
            best_category = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_category]
        
        # Fallback to general category for low confidence
        if best_score < 0.2:
            best_category = "general"
            best_score = 0.3
        
        # Validate category exists before accessing
        if best_category not in self.intents:
            best_category = "general"
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
