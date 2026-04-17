"""Route harness packets to MINDEX-grounded LLM, pure Nemotron, NLM, or voice."""

from __future__ import annotations

from mycosoft_mas.harness.models import HarnessPacket, RouteType


class HarnessRouter:
    def classify(self, packet: HarnessPacket) -> RouteType:
        if packet.raw_sensor:
            return RouteType.NLM
        if packet.raw_audio is not None:
            return RouteType.PERSONAPLEX_VOICE
        if packet.metadata.get("no_mindex_grounding") or packet.metadata.get("no_grounding"):
            return RouteType.NEMOTRON
        # Default text: MINDEX unified search + Nemotron (search-in-LLM).
        return RouteType.MINDEX_GROUNDED
