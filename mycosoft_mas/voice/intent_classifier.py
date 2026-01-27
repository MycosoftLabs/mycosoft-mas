"""Intent Classifier - January 27, 2026"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class IntentCategory(Enum):
    GREETING = "greeting"
    FAREWELL = "farewell"
    CHITCHAT = "chitchat"
    QUERY = "query"
    COMMAND = "command"
    CONTROL = "control"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    HELP = "help"
    UNKNOWN = "unknown"

@dataclass
class ClassifiedIntent:
    category: IntentCategory
    confidence: float
    requires_tool: bool
    requires_confirmation: bool
    entities: dict
    raw_text: str

class IntentClassifier:
    def __init__(self):
        self.greetings = [r"\b(hi|hello|hey|good morning|good afternoon)\b"]
        self.farewells = [r"\b(bye|goodbye|see you|later)\b"]
        self.queries = [r"\b(what is|what are|how many|show me|list|status|check)\b"]
        self.commands = [r"\b(turn on|turn off|set|create|delete|start|stop|run|send)\b"]
        self.controls = [r"\b(restart all|shutdown|reboot|backup|restore)\b"]
        self.confirms = [r"\b(yes|yeah|sure|confirm|proceed|go ahead)\b"]
        self.cancels = [r"\b(no|nope|cancel|stop|abort|never mind)\b"]
        self.helps = [r"\b(help|assist|what can you do)\b"]
        self.destructive = ["delete", "remove", "destroy", "shutdown", "restart all", "clear", "reset"]
    
    def classify(self, text: str) -> ClassifiedIntent:
        t = text.lower().strip()
        entities = self._extract_entities(t)
        
        if self._match(t, self.confirms):
            return ClassifiedIntent(IntentCategory.CONFIRMATION, 0.9, True, False, entities, text)
        if self._match(t, self.cancels):
            return ClassifiedIntent(IntentCategory.CANCELLATION, 0.9, True, False, entities, text)
        if self._match(t, self.controls):
            return ClassifiedIntent(IntentCategory.CONTROL, 0.85, True, True, entities, text)
        if self._match(t, self.commands):
            need_confirm = any(k in t for k in self.destructive)
            return ClassifiedIntent(IntentCategory.COMMAND, 0.8, True, need_confirm, entities, text)
        if self._match(t, self.queries):
            return ClassifiedIntent(IntentCategory.QUERY, 0.8, True, False, entities, text)
        if self._match(t, self.helps):
            return ClassifiedIntent(IntentCategory.HELP, 0.85, False, False, entities, text)
        if self._match(t, self.greetings):
            return ClassifiedIntent(IntentCategory.GREETING, 0.9, False, False, entities, text)
        if self._match(t, self.farewells):
            return ClassifiedIntent(IntentCategory.FAREWELL, 0.9, False, False, entities, text)
        return ClassifiedIntent(IntentCategory.CHITCHAT, 0.5, False, False, entities, text)
    
    def _match(self, text, patterns):
        return any(re.search(p, text, re.I) for p in patterns)
    
    def _extract_entities(self, text):
        entities = {}
        nums = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
        if nums:
            entities["numbers"] = nums
        return entities

_classifier = None
def get_classifier():
    global _classifier
    if not _classifier:
        _classifier = IntentClassifier()
    return _classifier
