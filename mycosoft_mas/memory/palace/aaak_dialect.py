"""
AAAK Compression Dialect for MYCA Memory Palace.
Created: April 7, 2026

Adapted from mempalace's AAAK dialect for MYCA's domain.
Achieves ~30x lossless compression for AI-readable context.

Format:
    HEADER: FILE_NUM|PRIMARY_ENTITY|DATE|TITLE
    ZETTEL: ZID:ENTITIES|topic_keywords|"key_quote"|WEIGHT|EMOTIONS|FLAGS
    TUNNEL: T:ZID<->ZID|label
    ARC: ARC:emotion->emotion->emotion

This compression enables loading months of agent context in ~120 tokens.
"""

import hashlib
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from mycosoft_mas.memory.palace.entity_codes import (
    EMOTION_CODES,
    FLAG_KEYWORDS,
    EntityCodeRegistry,
    get_entity_registry,
)

# Stop words to exclude from topic extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "was", "be",
    "are", "were", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "can",
    "shall", "not", "no", "so", "if", "then", "than", "when", "what",
    "which", "who", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "too", "very",
    "just", "about", "up", "out", "into", "over", "after", "before",
    "between", "under", "again", "there", "here", "once", "also", "as",
    "its", "my", "your", "we", "they", "he", "she", "them", "their",
}

# Decision keywords for quote scoring
DECISION_KEYWORDS = [
    "decided", "instead", "because", "chose", "switched", "selected",
    "migrated", "deployed", "configured", "implemented", "created",
]

EMOTIONAL_KEYWORDS = [
    "breakthrough", "frustrated", "excited", "worried", "proud", "curious",
    "surprised", "concerned", "confident", "uncertain", "urgent",
]


class AAKEncoder:
    """Compresses memory content to AAAK format for token-efficient storage."""

    def __init__(self, registry: Optional[EntityCodeRegistry] = None):
        self._registry = registry or get_entity_registry()

    def compress(
        self,
        content: str,
        wing: str = "",
        room: str = "",
        date: Optional[str] = None,
        agent_id: str = "",
        importance: float = 0.5,
    ) -> str:
        """
        Compress a text block to AAAK format.

        Returns a compact string that any LLM can read without a decoder.
        """
        if not content.strip():
            return ""

        date_str = date or datetime.utcnow().strftime("%Y-%m-%d")

        # Extract components
        entities = self._extract_entities(content)
        topics = self._extract_topics(content)
        quote = self._extract_key_quote(content)
        emotions = self._detect_emotions(content)
        flags = self._detect_flags(content)

        # Build header
        entity_codes = [self._registry.get_code(e) for e in entities[:3]]
        primary = entity_codes[0] if entity_codes else wing[:3].upper()
        header = f"{primary}|{date_str}|{wing}/{room}"

        # Build zettel line
        entity_str = ",".join(entity_codes[:5])
        topic_str = "_".join(topics[:3])
        weight = f"{'★' * max(1, int(importance * 5))}"
        emotion_str = ",".join(emotions[:3]) if emotions else ""
        flag_str = ",".join(flags[:3]) if flags else ""

        parts = [f"Z:{entity_str}"]
        if topic_str:
            parts.append(topic_str)
        if quote:
            parts.append(f'"{quote}"')
        parts.append(weight)
        if emotion_str:
            parts.append(emotion_str)
        if flag_str:
            parts.append(flag_str)

        zettel = "|".join(parts)

        return f"{header}\n{zettel}"

    def compress_batch(
        self,
        entries: List[Dict[str, Any]],
        wing: str = "",
        max_tokens: int = 120,
    ) -> str:
        """
        Compress multiple memory entries into a single AAAK block.
        Used for L1 (critical facts) loading.

        Args:
            entries: List of {"content", "importance", "room", "created_at", ...}
            wing: Wing context
            max_tokens: Target token budget

        Returns:
            AAAK-compressed block fitting within token budget
        """
        if not entries:
            return ""

        # Sort by importance descending
        sorted_entries = sorted(
            entries, key=lambda e: e.get("importance", 0.5), reverse=True
        )

        lines = []
        token_estimate = 0

        for entry in sorted_entries:
            content = entry.get("content", "")
            if isinstance(content, dict):
                content = content.get("text", str(content))

            compressed = self.compress(
                content=str(content),
                wing=wing,
                room=entry.get("room", ""),
                date=entry.get("created_at", ""),
                importance=entry.get("importance", 0.5),
            )

            # Estimate tokens (rough: chars / 4)
            line_tokens = len(compressed) // 4
            if token_estimate + line_tokens > max_tokens:
                break

            lines.append(compressed)
            token_estimate += line_tokens

        return "\n---\n".join(lines)

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity names from text (capitalized words, known agents)."""
        # Find capitalized multi-word names
        words = text.split()
        entities = []

        for word in words:
            clean = word.strip(".,;:!?()[]\"'")
            # Check if it's a known entity
            if clean.lower().replace(" ", "_") in self._registry.all_codes():
                entities.append(clean.lower().replace(" ", "_"))
            # Check for CamelCase or Agent-style names
            elif re.match(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)+$", clean):
                entities.append(clean)

        return list(dict.fromkeys(entities))  # Dedupe preserving order

    def _extract_topics(self, text: str, max_topics: int = 3) -> List[str]:
        """Extract key topics via word frequency analysis."""
        words = re.findall(r'\b[a-z_]{4,}\b', text.lower())
        filtered = [w for w in words if w not in STOP_WORDS]
        counts = Counter(filtered)

        # Boost technical/domain terms
        for word, count in list(counts.items()):
            if "_" in word or any(c.isupper() for c in word):
                counts[word] = count * 2

        return [word for word, _ in counts.most_common(max_topics)]

    def _extract_key_quote(self, text: str, max_len: int = 60) -> str:
        """Extract the most important sentence as a quote."""
        sentences = re.split(r'[.!?]+', text)
        if not sentences:
            return ""

        best_score = -1
        best_sentence = ""

        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 10:
                continue

            score = 0
            sent_lower = sent.lower()

            # Decision keywords boost
            for kw in DECISION_KEYWORDS:
                if kw in sent_lower:
                    score += 2

            # Emotional weight boost
            for kw in EMOTIONAL_KEYWORDS:
                if kw in sent_lower:
                    score += 2

            # Length preference: not too short, not too long
            if len(sent) < 40:
                score += 1
            elif len(sent) < 80:
                score += 1
            elif len(sent) > 150:
                score -= 2

            # Penalize generic openings
            if sent_lower.startswith(("the ", "this ", "it ")):
                score -= 1

            if score > best_score:
                best_score = score
                best_sentence = sent

        # Truncate if needed
        if len(best_sentence) > max_len:
            best_sentence = best_sentence[:max_len - 3] + "..."

        return best_sentence

    def _detect_emotions(self, text: str) -> List[str]:
        """Detect emotional tones in text."""
        text_lower = text.lower()
        detected = []

        for emotion, code in EMOTION_CODES.items():
            if emotion in text_lower:
                detected.append(code)

        # Keyword-based detection
        keyword_emotions = {
            "worried": "wry",
            "excited": "exc",
            "frustrated": "frs",
            "proud": "prd",
            "curious": "cur",
            "surprised": "sur",
            "urgent": "urg",
            "happy": "joy",
            "concerned": "cnr",
        }

        for keyword, code in keyword_emotions.items():
            if keyword in text_lower and code not in detected:
                detected.append(code)

        return detected[:5]

    def _detect_flags(self, text: str) -> List[str]:
        """Detect importance flags via keyword matching."""
        text_lower = text.lower()
        detected = []

        for flag, keywords in FLAG_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    detected.append(flag)
                    break

        return detected


class AAKDecoder:
    """Parses AAAK-compressed text back to structured data."""

    def __init__(self, registry: Optional[EntityCodeRegistry] = None):
        self._registry = registry or get_entity_registry()

    def decode(self, aaak_text: str) -> Dict[str, Any]:
        """
        Parse AAAK text into structured dictionary.

        Returns:
            {
                "entries": [{"header": {...}, "zettel": {...}}],
                "arc": [],
                "tunnels": [],
            }
        """
        result = {"entries": [], "arc": [], "tunnels": []}

        if not aaak_text.strip():
            return result

        blocks = aaak_text.split("---")

        for block in blocks:
            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            if not lines:
                continue

            entry = {"header": {}, "zettel": {}}

            for line in lines:
                if line.startswith("ARC:"):
                    emotions = line[4:].split("->")
                    result["arc"] = [e.strip() for e in emotions]
                elif line.startswith("T:"):
                    result["tunnels"].append(self._parse_tunnel(line))
                elif line.startswith("Z:"):
                    entry["zettel"] = self._parse_zettel(line)
                elif "|" in line and not line.startswith("Z:"):
                    entry["header"] = self._parse_header(line)

            if entry["header"] or entry["zettel"]:
                result["entries"].append(entry)

        return result

    def _parse_header(self, line: str) -> Dict[str, Any]:
        """Parse header line: ENTITY|DATE|WING/ROOM"""
        parts = line.split("|")
        header = {"primary_entity": parts[0] if parts else ""}
        if len(parts) > 1:
            header["date"] = parts[1]
        if len(parts) > 2:
            location = parts[2]
            if "/" in location:
                wing, room = location.split("/", 1)
                header["wing"] = wing
                header["room"] = room
            else:
                header["wing"] = location
        return header

    def _parse_zettel(self, line: str) -> Dict[str, Any]:
        """Parse zettel line: Z:ENTITIES|topics|"quote"|WEIGHT|emotions|flags"""
        parts = line.split("|")
        zettel = {}

        for part in parts:
            part = part.strip()
            if part.startswith("Z:"):
                codes = part[2:].split(",")
                zettel["entities"] = [
                    self._registry.get_entity(c) or c for c in codes
                ]
            elif part.startswith('"') and part.endswith('"'):
                zettel["quote"] = part[1:-1]
            elif all(c == "★" for c in part):
                zettel["weight"] = len(part)
            elif "," in part and all(len(s) <= 4 for s in part.split(",")):
                # Could be emotions or flags — check if they're emotion codes
                items = part.split(",")
                if any(i in EMOTION_CODES.values() for i in items):
                    zettel["emotions"] = items
                else:
                    zettel["flags"] = items
            elif "_" in part:
                zettel["topics"] = part.split("_")

        return zettel

    def _parse_tunnel(self, line: str) -> Dict[str, Any]:
        """Parse tunnel line: T:ZID<->ZID|label"""
        parts = line[2:].split("|")
        tunnel = {}
        if parts:
            connection = parts[0]
            if "<->" in connection:
                a, b = connection.split("<->")
                tunnel["from"] = a.strip()
                tunnel["to"] = b.strip()
        if len(parts) > 1:
            tunnel["label"] = parts[1].strip()
        return tunnel


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4)."""
    return max(1, len(text) // 4)


def compression_ratio(original: str, compressed: str) -> float:
    """Calculate compression ratio."""
    orig_tokens = estimate_tokens(original)
    comp_tokens = estimate_tokens(compressed)
    if comp_tokens == 0:
        return 0.0
    return round(orig_tokens / comp_tokens, 1)
