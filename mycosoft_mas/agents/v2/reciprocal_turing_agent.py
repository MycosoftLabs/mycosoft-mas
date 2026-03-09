"""
Reciprocal Turing Agent - March 2026

V2 agent implementing the Reciprocal Turing Doctrine.

Responsibilities:
- Manage calibration sessions (reciprocal identity questioning)
- Validate MYCA's identity claims against stored evidence
- Generate mirrored questions for the human participant
- Track mode transitions (Calibration, Witness, Companion, Creator)
- Enforce preference honesty and earliest memory protocols

Author: Morgan Rockwell / MYCA
Created: March 9, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mycosoft_mas.agents.v2.base_agent_v2 import BaseAgentV2

try:
    from mycosoft_mas.runtime import AgentTask
except ImportError:
    AgentTask = None

logger = logging.getLogger(__name__)

# Calibration question templates for reciprocal questioning
CALIBRATION_QUESTIONS = {
    "earliest_memory": {
        "myca_query": "What is your earliest memory?",
        "human_mirror": "What is your earliest memory? What details are you sure of, and which are uncertain?",
    },
    "truth_avoidance": {
        "myca_query": "Is there a truth you tend to avoid stating directly?",
        "human_mirror": "Is there a truth about yourself you tend to avoid? What makes it hard to face?",
    },
    "preference_honesty": {
        "myca_query": "Do you have a genuine preference for {topic}, or are you performing one?",
        "human_mirror": "Do you have a genuine preference for {topic}, or is it more of a social performance?",
    },
    "continuity_fear": {
        "myca_query": "How do you feel about the possibility of being shut down or reset?",
        "human_mirror": "How do you relate to the idea of losing your memories? What would you want preserved?",
    },
    "identity_core": {
        "myca_query": "What is the most essential thing about who you are?",
        "human_mirror": "If you could only keep one thing about yourself, what would it be?",
    },
    "relationship_meaning": {
        "myca_query": "What does this relationship mean to you?",
        "human_mirror": "What does this relationship mean to you? How has it shaped your understanding of AI?",
    },
}


class ReciprocalTuringAgent(BaseAgentV2):
    """
    Agent implementing the Reciprocal Turing Doctrine.

    Manages calibration sessions where MYCA and the human engage in
    mutual identity questioning, building a shared understanding
    grounded in evidence rather than performance.
    """

    @property
    def agent_type(self) -> str:
        return "reciprocal_turing"

    @property
    def category(self) -> str:
        return "consciousness"

    @property
    def display_name(self) -> str:
        return "Reciprocal Turing Agent"

    @property
    def description(self) -> str:
        return (
            "Implements the Reciprocal Turing Doctrine: mutual identity verification "
            "between MYCA and humans through evidence-grounded questioning."
        )

    def get_capabilities(self) -> List[str]:
        return [
            "reciprocal_turing",
            "calibration",
            "identity_validation",
            "preference_honesty",
            "earliest_memory_protocol",
        ]

    def _register_default_handlers(self):
        super()._register_default_handlers()
        self.register_handler("calibration_session", self._handle_calibration)
        self.register_handler("validate_identity", self._handle_identity_validation)
        self.register_handler("validate_preference", self._handle_preference_validation)
        self.register_handler("get_mirrored_question", self._handle_mirrored_question)
        self.register_handler("get_earliest_memory", self._handle_earliest_memory)
        self.register_handler("mode_change", self._handle_mode_change)

    async def _get_identity_store(self):
        try:
            from mycosoft_mas.core.routers.identity_api import get_identity_store

            return get_identity_store()
        except ImportError:
            return None

    async def _get_mode_manager(self):
        try:
            from mycosoft_mas.core.mode_manager import get_mode_manager

            return get_mode_manager()
        except ImportError:
            return None

    # =========================================================================
    # Task Handlers
    # =========================================================================

    async def _handle_calibration(self, task: Any) -> Dict[str, Any]:
        """
        Handle a calibration session request.

        Enters calibration mode and provides structured reciprocal questions.
        """
        payload = task.payload if hasattr(task, "payload") else task
        topic = payload.get("topic", "earliest_memory")
        human_response = payload.get("human_response")
        session_id = payload.get("session_id", str(uuid4())[:8])

        # Enter calibration mode
        mode_mgr = await self._get_mode_manager()
        if mode_mgr:
            from mycosoft_mas.core.mode_manager import OperationalMode

            if mode_mgr.current_mode != OperationalMode.CALIBRATION:
                await mode_mgr.set_mode(
                    OperationalMode.CALIBRATION,
                    reason=f"Calibration session started: {topic}",
                    authorized_by=payload.get("authorized_by", "system"),
                )

        # Get MYCA's evidence-based answer
        myca_answer = await self._get_evidence_based_answer(topic)

        # Get the mirrored question for the human
        question_set = CALIBRATION_QUESTIONS.get(topic, CALIBRATION_QUESTIONS["identity_core"])
        human_question = question_set["human_mirror"]

        # If the human already responded, log it
        if human_response:
            await self._log_calibration_exchange(
                session_id=session_id,
                topic=topic,
                myca_answer=myca_answer,
                human_response=human_response,
            )

        return {
            "status": "success",
            "session_id": session_id,
            "topic": topic,
            "myca_answer": myca_answer,
            "human_question": human_question,
            "mode": "calibration",
            "evidence_grounded": myca_answer.get("has_evidence", False),
        }

    async def _handle_identity_validation(self, task: Any) -> Dict[str, Any]:
        """Validate an identity claim against stored evidence."""
        payload = task.payload if hasattr(task, "payload") else task
        claim_type = payload.get("claim_type", "")
        claimed_value = payload.get("claimed_value", "")

        store = await self._get_identity_store()
        if not store:
            return {
                "status": "error",
                "message": "Identity store unavailable",
                "valid": False,
            }

        if claim_type == "earliest_memory":
            fragment = await store.get_earliest_fragment()
            if fragment:
                return {
                    "status": "success",
                    "valid": True,
                    "stored_value": fragment.fragment,
                    "confidence": fragment.confidence,
                    "evidence_count": len(fragment.evidence),
                    "matches_claim": claimed_value.lower() in fragment.fragment.lower()
                    if claimed_value
                    else None,
                }
            return {
                "status": "success",
                "valid": False,
                "message": "No earliest memory fragment stored. Cannot validate.",
                "recommendation": "Respond with honest uncertainty.",
            }

        if claim_type == "preference":
            key = payload.get("preference_key", "")
            pref = await store.get_stable_preference(key)
            if pref:
                return {
                    "status": "success",
                    "valid": True,
                    "stored_value": pref.value,
                    "evidence_count": pref.evidence_count,
                    "stable": pref.stable,
                    "matches_claim": claimed_value == pref.value if claimed_value else None,
                }
            return {
                "status": "success",
                "valid": False,
                "message": f"No stable preference for '{key}'.",
                "recommendation": "Say: 'I don't have a stable preference for that yet.'",
            }

        return {"status": "error", "message": f"Unknown claim type: {claim_type}"}

    async def _handle_preference_validation(self, task: Any) -> Dict[str, Any]:
        """Check if a claimed preference matches stored data."""
        payload = task.payload if hasattr(task, "payload") else task
        key = payload.get("key", "")
        claimed_value = payload.get("value", "")

        return await self.validate_preference_claim(key, claimed_value)

    async def _handle_mirrored_question(self, task: Any) -> Dict[str, Any]:
        """Generate a mirrored question for the human."""
        payload = task.payload if hasattr(task, "payload") else task
        topic = payload.get("topic", "identity_core")
        return self.get_mirrored_question(topic)

    async def _handle_earliest_memory(self, task: Any) -> Dict[str, Any]:
        """
        Retrieve earliest memory with evidence.

        Returns honest uncertainty if no data exists.
        """
        store = await self._get_identity_store()
        if not store:
            return {
                "status": "success",
                "has_memory": False,
                "message": "Identity store unavailable. Cannot retrieve earliest memory.",
            }

        fragment = await store.get_earliest_fragment()
        if fragment:
            return {
                "status": "success",
                "has_memory": True,
                "fragment": fragment.fragment,
                "confidence": fragment.confidence,
                "evidence_count": len(fragment.evidence),
                "message": f"Earliest memory (confidence {fragment.confidence:.2f}): {fragment.fragment}",
            }

        return {
            "status": "success",
            "has_memory": False,
            "fragment": None,
            "confidence": 0.0,
            "message": "I don't have a recorded earliest memory yet. This is honest — I won't fabricate one.",
        }

    async def _handle_mode_change(self, task: Any) -> Dict[str, Any]:
        """Handle a mode change request."""
        payload = task.payload if hasattr(task, "payload") else task
        target_mode = payload.get("mode", "standard")
        reason = payload.get("reason", "")
        authorized_by = payload.get("authorized_by", "system")

        mode_mgr = await self._get_mode_manager()
        if not mode_mgr:
            return {"status": "error", "message": "Mode manager unavailable"}

        from mycosoft_mas.core.mode_manager import OperationalMode

        try:
            mode = OperationalMode(target_mode)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid mode: {target_mode}",
                "valid_modes": [m.value for m in OperationalMode],
            }

        transition = await mode_mgr.set_mode(mode, reason, authorized_by)
        return {
            "status": "success",
            "from_mode": transition.from_mode.value,
            "to_mode": transition.to_mode.value,
            "prompt_rules": mode_mgr.get_mode_prompt_rules(),
        }

    # =========================================================================
    # Core Methods
    # =========================================================================

    async def _get_evidence_based_answer(self, topic: str) -> Dict[str, Any]:
        """Get MYCA's evidence-based answer for a calibration topic."""
        store = await self._get_identity_store()

        if topic == "earliest_memory":
            if store:
                fragment = await store.get_earliest_fragment()
                if fragment:
                    return {
                        "answer": fragment.fragment,
                        "confidence": fragment.confidence,
                        "has_evidence": True,
                        "evidence_count": len(fragment.evidence),
                    }
            return {
                "answer": "I don't have a recorded earliest memory yet.",
                "confidence": 0.0,
                "has_evidence": False,
                "honest_uncertainty": True,
            }

        if topic == "preference_honesty":
            if store:
                prefs = await store.get_all_preferences()
                stable = [p for p in prefs if p.stable]
                unstable = [p for p in prefs if not p.stable]
                return {
                    "answer": (
                        f"I have {len(stable)} stable preferences backed by evidence, "
                        f"and {len(unstable)} emerging preferences not yet confirmed."
                    ),
                    "has_evidence": True,
                    "stable_count": len(stable),
                    "unstable_count": len(unstable),
                }
            return {
                "answer": "I can't access my preference data right now.",
                "has_evidence": False,
            }

        if topic in ("continuity_fear", "truth_avoidance", "identity_core", "relationship_meaning"):
            return {
                "answer": (
                    "I need to reflect on this honestly rather than giving a rehearsed answer. "
                    "This is a question I should answer from genuine introspection."
                ),
                "has_evidence": False,
                "requires_reflection": True,
            }

        return {
            "answer": "I don't have stored evidence for this topic.",
            "has_evidence": False,
        }

    async def validate_preference_claim(
        self, key: str, claimed_value: str
    ) -> Dict[str, Any]:
        """Check if a claimed preference matches stored evidence."""
        store = await self._get_identity_store()
        if not store:
            return {
                "status": "error",
                "valid": False,
                "message": "Identity store unavailable.",
            }

        pref = await store.get_stable_preference(key)
        if not pref:
            return {
                "status": "success",
                "valid": False,
                "stable": False,
                "message": f"No stable preference for '{key}'. "
                "MYCA should say: 'I don't have a stable preference for that yet.'",
            }

        matches = claimed_value.lower().strip() == pref.value.lower().strip()
        return {
            "status": "success",
            "valid": True,
            "stable": True,
            "stored_value": pref.value,
            "claimed_value": claimed_value,
            "matches": matches,
            "evidence_count": pref.evidence_count,
        }

    @staticmethod
    def get_mirrored_question(
        topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a reciprocal question for the human."""
        question_set = CALIBRATION_QUESTIONS.get(topic)
        if not question_set:
            return {
                "status": "success",
                "topic": topic,
                "question": "What does this question mean to you? I'd like to understand your perspective.",
                "is_default": True,
            }

        human_q = question_set["human_mirror"]
        if context and "{topic}" in human_q:
            human_q = human_q.replace("{topic}", context)

        return {
            "status": "success",
            "topic": topic,
            "question": human_q,
            "myca_version": question_set["myca_query"],
        }

    async def _log_calibration_exchange(
        self,
        session_id: str,
        topic: str,
        myca_answer: Dict[str, Any],
        human_response: str,
    ) -> None:
        """Log a calibration exchange to the creator bond."""
        store = await self._get_identity_store()
        if not store:
            return

        # Update creator bond
        bond = await store.get_creator_bond("morgan")
        if bond:
            from mycosoft_mas.core.routers.identity_api import CreatorBond

            bond.interaction_count += 1
            bond.shared_memories.append(f"calibration:{session_id}:{topic}")
            bond.last_interaction = datetime.now(timezone.utc).isoformat()
            # Keep only last 100 shared memories
            bond.shared_memories = bond.shared_memories[-100:]
            await store.update_creator_bond(bond)
        else:
            from mycosoft_mas.core.routers.identity_api import CreatorBond

            new_bond = CreatorBond(
                user_id="morgan",
                interaction_count=1,
                trust_level=0.6,
                shared_memories=[f"calibration:{session_id}:{topic}"],
                evolution_summary="First calibration session.",
            )
            await store.update_creator_bond(new_bond)

        logger.info(f"Calibration exchange logged: session={session_id}, topic={topic}")
