"""
Voice v9 Event Translation Engine - March 2, 2026.

Translates raw MDP, MAS task, tool completion, NLM/CREP payloads into SpeechworthyEvent.
Uses MDP_PROTOCOL_CONTRACTS_MAR07_2026.md for device/gateway payload normalization.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mycosoft_mas.voice_v9.schemas import EventSource, SpeechworthyEvent


class EventTranslationEngine:
    """
    Normalizes raw events from multiple sources into SpeechworthyEvent.
    Both speech and UI consume the output for truth consistency.
    """

    def translate(
        self,
        session_id: str,
        source: EventSource,
        raw: Dict[str, Any],
    ) -> Optional[SpeechworthyEvent]:
        """
        Translate a raw payload into a SpeechworthyEvent.
        Returns None if the payload cannot be meaningfully translated.
        """
        if source == EventSource.MDP_DEVICE:
            return self._translate_mdp_device(session_id, raw)
        if source == EventSource.MAS_TASK:
            return self._translate_mas_task(session_id, raw)
        if source == EventSource.TOOL_COMPLETION:
            return self._translate_tool_completion(session_id, raw)
        if source == EventSource.CREP:
            return self._translate_crep(session_id, raw)
        if source == EventSource.NLM:
            return self._translate_nlm(session_id, raw)
        if source == EventSource.MYCORRHIZAE:
            return self._translate_mycorrhizae(session_id, raw)
        if source == EventSource.SYSTEM:
            return self._translate_system(session_id, raw)
        return None

    def _translate_mdp_device(
        self, session_id: str, raw: Dict[str, Any]
    ) -> Optional[SpeechworthyEvent]:
        """
        MDP device telemetry/event per MDP_PROTOCOL_CONTRACTS.
        Supports: TELEMETRY, EVENT, HELLO shapes from gateway/device upstream.
        """
        device_id = raw.get("deviceId") or raw.get("device_id") or "unknown"
        readings = raw.get("readings", [])
        event_type = raw.get("type") or raw.get("event_type", "telemetry")

        if event_type in ("estop", "fault", "link_down"):
            summary = f"Device {device_id}: {event_type}"
            urgency = 0.9
            confidence = 1.0
        elif event_type == "telemetry" and readings:
            r = readings[0] if isinstance(readings[0], dict) else {}
            temp = raw.get("temperature") or r.get("temperature") or r.get("temp")
            humidity = raw.get("humidity") or r.get("humidity")
            parts = []
            if temp is not None:
                parts.append(f"{temp:.1f}°C")
            if humidity is not None:
                parts.append(f"{humidity:.0f}% humidity")
            summary = f"Device {device_id}: " + (", ".join(parts) if parts else "new reading")
            urgency = 0.3
            confidence = 0.85
        elif event_type == "hello":
            summary = f"Device {device_id} connected"
            urgency = 0.5
            confidence = 1.0
        else:
            summary = f"Device {device_id}: {event_type}"
            urgency = 0.4
            confidence = 0.8

        provenance = f"mdp_device:{device_id}"
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.MDP_DEVICE,
            summary=summary,
            urgency=urgency,
            confidence=confidence,
            raw_payload=raw,
            provenance=provenance,
            metadata={"device_id": device_id, "event_type": event_type},
        )

    def _translate_mas_task(
        self, session_id: str, raw: Dict[str, Any]
    ) -> Optional[SpeechworthyEvent]:
        """MAS task started/completed/failed."""
        task_id = raw.get("task_id") or raw.get("id", "unknown")
        status = raw.get("status") or raw.get("state", "unknown")
        name = raw.get("name") or raw.get("task_type", "task")

        if status in ("failed", "error"):
            summary = f"Task {name} failed"
            urgency = 0.7
            confidence = 0.95
        elif status in ("completed", "done"):
            summary = raw.get("summary") or f"Task {name} completed"
            urgency = 0.4
            confidence = 0.9
        elif status in ("started", "running"):
            summary = raw.get("summary") or f"Task {name} started"
            urgency = 0.3
            confidence = 0.85
        else:
            summary = raw.get("summary") or f"Task {name}: {status}"
            urgency = 0.4
            confidence = 0.8

        provenance = f"mas_task:{task_id}"
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.MAS_TASK,
            summary=summary,
            urgency=urgency,
            confidence=confidence,
            raw_payload=raw,
            provenance=provenance,
            metadata={"task_id": task_id, "status": status},
        )

    def _translate_tool_completion(
        self, session_id: str, raw: Dict[str, Any]
    ) -> Optional[SpeechworthyEvent]:
        """Tool/agent completion event."""
        tool = raw.get("tool") or raw.get("agent", "tool")
        success = raw.get("success", True)
        result_summary = raw.get("result_summary") or raw.get("summary", "")

        if success:
            summary = result_summary or f"{tool} completed"
            urgency = 0.4
            confidence = 0.9
        else:
            summary = raw.get("error") or result_summary or f"{tool} failed"
            urgency = 0.6
            confidence = 0.85

        provenance = f"tool_completion:{tool}"
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.TOOL_COMPLETION,
            summary=summary,
            urgency=urgency,
            confidence=confidence,
            raw_payload=raw,
            provenance=provenance,
            metadata={"tool": tool, "success": success},
        )

    def _translate_crep(self, session_id: str, raw: Dict[str, Any]) -> Optional[SpeechworthyEvent]:
        """CREP worldview / aviation / maritime / fishing intel summary."""
        category = raw.get("category") or raw.get("type", "update")
        summary_text = raw.get("summary") or raw.get("worldview_summary", "")
        if not summary_text and isinstance(raw.get("items"), list):
            n = len(raw["items"])
            summary_text = f"CREP {category}: {n} items"
        if not summary_text:
            summary_text = f"CREP {category} update"

        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.CREP,
            summary=summary_text[:500],
            urgency=raw.get("urgency", 0.4),
            confidence=raw.get("confidence", 0.85),
            raw_payload=raw,
            provenance="crep",
            metadata={"category": category},
        )

    def _translate_nlm(self, session_id: str, raw: Dict[str, Any]) -> Optional[SpeechworthyEvent]:
        """NLM (Nature Learning Model) summary - mycology/natural sciences."""
        summary_text = raw.get("summary") or raw.get("nlm_summary", "")
        if not summary_text:
            summary_text = "NLM observation update"
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.NLM,
            summary=summary_text[:500],
            urgency=raw.get("urgency", 0.35),
            confidence=raw.get("confidence", 0.88),
            raw_payload=raw,
            provenance="nlm",
            metadata={},
        )

    def _translate_mycorrhizae(
        self, session_id: str, raw: Dict[str, Any]
    ) -> Optional[SpeechworthyEvent]:
        """Mycorrhizae/MMP telemetry (staged; contract from MYCORRHIZAE_MYCA_TELEMETRY_BRIDGE)."""
        device_id = raw.get("device_id") or raw.get("deviceId", "unknown")
        payload_type = raw.get("payload_type") or raw.get("type", "telemetry")
        summary = raw.get("summary") or f"Mycorrhizae {device_id}: {payload_type}"
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.MYCORRHIZAE,
            summary=summary,
            urgency=raw.get("urgency", 0.4),
            confidence=raw.get("confidence", 0.8),
            raw_payload=raw,
            provenance=f"mycorrhizae:{device_id}",
            metadata={"device_id": device_id, "payload_type": payload_type},
        )

    def _translate_system(
        self, session_id: str, raw: Dict[str, Any]
    ) -> Optional[SpeechworthyEvent]:
        """System-level events."""
        summary = raw.get("summary") or raw.get("message", "System event")
        return SpeechworthyEvent(
            session_id=session_id,
            source=EventSource.SYSTEM,
            summary=summary,
            urgency=raw.get("urgency", 0.5),
            confidence=raw.get("confidence", 0.95),
            raw_payload=raw,
            provenance="system",
            metadata=raw.get("metadata", {}),
        )


_engine: Optional[EventTranslationEngine] = None


def get_event_translation_engine() -> EventTranslationEngine:
    global _engine
    if _engine is None:
        _engine = EventTranslationEngine()
    return _engine
