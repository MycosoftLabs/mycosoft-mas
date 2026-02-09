"""
TONL Token Compressor
Provides prompt compression for LLM calls to reduce token usage and cost.
This is a basic rule-based implementation that can be replaced with the
actual TONL library when available.

Created: February 9, 2026
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Common filler phrases that can be shortened
PHRASE_ABBREVIATIONS: Dict[str, str] = {
    "in order to": "to",
    "as well as": "and",
    "due to the fact that": "because",
    "in the event that": "if",
    "for the purpose of": "for",
    "with regard to": "regarding",
    "with respect to": "regarding",
    "in addition to": "besides",
    "on the other hand": "however",
    "at this point in time": "now",
    "at the present time": "now",
    "in the near future": "soon",
    "a large number of": "many",
    "a significant number of": "many",
    "the vast majority of": "most",
    "in spite of the fact that": "although",
    "it is important to note that": "",
    "it should be noted that": "",
    "it is worth mentioning that": "",
    "as a matter of fact": "",
    "needless to say": "",
    "it goes without saying that": "",
    "please note that": "",
    "for your information": "",
    "as you can see": "",
    "as mentioned above": "",
    "as previously stated": "",
    "in other words": "i.e.",
    "for example": "e.g.",
    "that is to say": "i.e.",
    "in the case of": "for",
    "with the exception of": "except",
    "on a regular basis": "regularly",
    "at the end of the day": "ultimately",
    "first and foremost": "first",
    "each and every": "every",
    "one and only": "only",
    "any and all": "all",
}

# Low-information sentence patterns (regex)
LOW_INFO_PATTERNS = [
    r"^(This is|Here is|Here are|The following is|Below is) (a |an |the )?(brief |short )?(overview|summary|description|list|explanation)\b.*[.!]$",
    r"^(Let me|I will|I would like to|Allow me to) (explain|describe|outline|summarize|provide)\b.*[.!]$",
    r"^(As you know|As we know|As everyone knows|Obviously|Clearly|Of course)\b.*[.!]$",
    r"^(Thank you for|Thanks for) (your |the )?(question|asking|inquiry)\b.*[.!]$",
    r"^(I hope this helps|Hope this helps|I hope that helps)\b.*[.!?]$",
]

# Approximate tokens-per-character ratio (GPT-family average)
CHARS_PER_TOKEN = 4.0


class TONLCompressor:
    """
    Token-Optimized Natural Language compressor.

    Reduces prompt size by removing redundant whitespace, abbreviating
    common verbose phrases, and stripping low-information sentences.

    Usage:
        compressor = TONLCompressor()
        compressed = compressor.compress(long_prompt, target_ratio=0.55)
        savings = compressor.estimate_savings(long_prompt)
    """

    def __init__(self) -> None:
        # Pre-compile low-info patterns
        self._low_info_re = [
            re.compile(pat, re.IGNORECASE) for pat in LOW_INFO_PATTERNS
        ]
        # Sort abbreviations longest-first so longer phrases match first
        self._abbrev_pairs = sorted(
            PHRASE_ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True
        )

    def compress(self, text: str, target_ratio: float = 0.55) -> str:
        """
        Compress text to reduce token count.

        Args:
            text: The input text to compress.
            target_ratio: Target compression ratio (0.55 = keep ~55% of tokens).
                          The compressor applies all rules and may not hit the
                          exact ratio; this guides aggressiveness.

        Returns:
            Compressed text string.
        """
        if not text or not text.strip():
            return text

        original_len = len(text)

        # Step 1: Normalize whitespace
        result = self._normalize_whitespace(text)

        # Step 2: Abbreviate verbose phrases
        result = self._abbreviate_phrases(result)

        # Step 3: Remove low-information sentences if we need more compression
        current_ratio = len(result) / original_len if original_len > 0 else 1.0
        if current_ratio > target_ratio:
            result = self._remove_low_info_sentences(result)

        # Step 4: Final whitespace cleanup
        result = self._normalize_whitespace(result)

        compressed_len = len(result)
        achieved_ratio = compressed_len / original_len if original_len > 0 else 1.0

        logger.info(
            "TONL compression: %d -> %d chars (%.1f%% of original, target was %.0f%%)",
            original_len,
            compressed_len,
            achieved_ratio * 100,
            target_ratio * 100,
        )

        return result

    def estimate_savings(self, text: str) -> Dict:
        """
        Estimate token and cost savings from compression.

        Args:
            text: The input text to analyze.

        Returns:
            Dictionary with:
                - tokens_before: Estimated token count of original text
                - tokens_after: Estimated token count after compression
                - tokens_saved: Number of tokens saved
                - compression_ratio: Ratio of compressed to original
                - estimated_cost_saving_usd: Approximate USD saved at $0.003/1K tokens
        """
        if not text or not text.strip():
            return {
                "tokens_before": 0,
                "tokens_after": 0,
                "tokens_saved": 0,
                "compression_ratio": 1.0,
                "estimated_cost_saving_usd": 0.0,
            }

        compressed = self.compress(text)

        tokens_before = self._estimate_tokens(text)
        tokens_after = self._estimate_tokens(compressed)
        tokens_saved = max(0, tokens_before - tokens_after)

        ratio = tokens_after / tokens_before if tokens_before > 0 else 1.0
        # Rough cost estimate at $0.003 per 1K input tokens (GPT-4 class)
        cost_saving = (tokens_saved / 1000) * 0.003

        return {
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_saved": tokens_saved,
            "compression_ratio": round(ratio, 3),
            "estimated_cost_saving_usd": round(cost_saving, 6),
        }

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count using character-based heuristic."""
        return max(1, int(len(text) / CHARS_PER_TOKEN))

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Collapse redundant whitespace while preserving paragraph breaks."""
        # Preserve double newlines (paragraph breaks) but collapse others
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Trim lines
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    def _abbreviate_phrases(self, text: str) -> str:
        """Replace verbose phrases with shorter equivalents."""
        result = text
        for long_form, short_form in self._abbrev_pairs:
            # Case-insensitive replacement preserving sentence flow
            pattern = re.compile(re.escape(long_form), re.IGNORECASE)
            result = pattern.sub(short_form, result)
        # Clean up double spaces from removed phrases
        result = re.sub(r"  +", " ", result)
        # Clean up leading spaces after sentence starts
        result = re.sub(r"\.\s{2,}", ". ", result)
        return result

    def _remove_low_info_sentences(self, text: str) -> str:
        """Remove sentences that carry little information."""
        lines = text.split("\n")
        filtered = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered.append(line)
                continue
            # Check each sentence in the line
            is_low_info = False
            for pattern in self._low_info_re:
                if pattern.match(stripped):
                    is_low_info = True
                    break
            if not is_low_info:
                filtered.append(line)
        return "\n".join(filtered)
