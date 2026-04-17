"""Harness engine — router, policy static YAML, MINDEX search-in-LLM, Nemotron, voice, NLM."""

from __future__ import annotations

import uuid

from mycosoft_mas.harness.config import HarnessConfig
from mycosoft_mas.harness.evaluator import HarnessEvaluator
from mycosoft_mas.harness.intention_brain import IntentionBrain
from mycosoft_mas.harness.mindex_client import MindexClient
from mycosoft_mas.harness.models import HarnessPacket, HarnessResult, RouteType
from mycosoft_mas.harness.nemotron_client import NemotronClient
from mycosoft_mas.harness.nlm_interface import NlmInterface
from mycosoft_mas.harness.persona_plex import PersonaPlexInterface
from mycosoft_mas.harness.planner import HarnessPlanner, attach_result_meta
from mycosoft_mas.harness.router import HarnessRouter
from mycosoft_mas.harness.static_search import StaticSearch
from mycosoft_mas.harness.static_system import StaticSystem


class HarnessEngine:
    """Central orchestrator — construct once at process startup."""

    def __init__(self, config: HarnessConfig | None = None) -> None:
        self.config = config or HarnessConfig.from_env()
        self.router = HarnessRouter()
        self.static_system = StaticSystem(self.config.static_answers_path)
        self.static_search = StaticSearch(self.config)
        self.nemotron = NemotronClient(self.config)
        self.personaplex = PersonaPlexInterface(self.config)
        self.intention = IntentionBrain(self.config.intention_db_path)
        self.planner = HarnessPlanner(self.intention)
        self.mindex = MindexClient(self.config)
        self.evaluator = HarnessEvaluator(self.mindex)
        self.nlm = NlmInterface(enabled=self.config.nlm_enabled)

    async def run(self, packet: HarnessPacket) -> HarnessResult:
        # Voice ingress: transcribe then clear audio so routing follows text semantics.
        if packet.raw_audio:
            heard = await self.personaplex.transcribe(packet.raw_audio)
            packet = packet.model_copy(update={"query": heard or "", "raw_audio": None})

        run_id = str(uuid.uuid4())
        route = self.router.classify(packet)
        plan = self.planner.plan(packet, route)

        static_answer = self.static_system.lookup(packet.query)
        if static_answer is not None:
            result = HarnessResult(
                route=RouteType.STATIC,
                text=static_answer,
                sources=["static_system"],
            )
            attach_result_meta(result, plan)
            await self._record(run_id, packet, result)
            return result

        if route == RouteType.NLM and packet.raw_sensor:
            frame = self.nlm.build_frame(packet.raw_sensor, 0.0, 0.0, 0.0)
            pred = self.nlm.predict(frame)
            self.intention.ingest_signal("nlm", pred)
            result = HarnessResult(
                route=RouteType.NLM,
                text=None,
                structured={"prediction": pred, "frame_stub": str(type(frame))},
                sources=["nlm"],
            )
            attach_result_meta(result, plan)
            await self._record(run_id, packet, result)
            return result

        types_override = packet.metadata.get("mindex_search_types")
        types = (
            str(types_override)
            if types_override is not None
            else self.config.default_unified_search_types
        )

        system: str
        out_route = route
        structured_extra: dict = {}

        use_mindex = (
            route == RouteType.MINDEX_GROUNDED and self.config.ground_queries_with_mindex
        )
        if use_mindex:
            ctx = await self.static_search.build_llm_context(
                packet.query or "",
                types=types,
            )
            system = (
                "You are MYCA harness assistant. Use the MINDEX retrieval context below when "
                "it is relevant to the user question; cite-or-align with it for factual "
                "claims about species, compounds, and observations. If the context block "
                "is empty or not relevant, answer helpfully and state uncertainty.\n\n"
                + (ctx.strip() or "(No MINDEX unified-search hits for this query.)")
            )
            structured_extra["mindex_context_chars"] = len(ctx)
            out_route = RouteType.MINDEX_GROUNDED
            sources = ["mindex_unified_search", "nemotron"]
        else:
            system = "You are MYCA harness assistant; be concise and factual."
            out_route = RouteType.NEMOTRON
            sources = ["nemotron"]

        text_chunks: list[str] = []
        prompt = packet.query or ""
        async for chunk in self.nemotron.generate(
            prompt,
            system=system,
            stream=False,
        ):
            text_chunks.append(chunk)
        text = "".join(text_chunks)

        result = HarnessResult(
            route=out_route,
            text=text,
            structured=structured_extra,
            sources=sources,
        )
        ev = await self.evaluator.verify_species_mention(text, None)
        result.needs_review = ev.get("needs_review", False)
        result.flags.extend(ev.get("reasons", []))

        if packet.prefer_voice and text:
            try:
                audio = await self.personaplex.speak(text)
                if audio:
                    result.audio = audio
                    result.sources.append("personaplex_tts")
            except Exception:
                pass

        attach_result_meta(result, plan)
        await self._record(run_id, packet, result)
        return result

    async def _record(self, run_id: str, packet: HarnessPacket, result: HarnessResult) -> None:
        await self.mindex.record_execution(
            run_id,
            [
                {
                    "query": packet.query,
                    "route": result.route.value,
                    "needs_review": result.needs_review,
                }
            ],
        )


_engine: HarnessEngine | None = None


def get_engine() -> HarnessEngine:
    global _engine
    if _engine is None:
        _engine = HarnessEngine()
    return _engine


def set_engine(engine: HarnessEngine | None) -> None:
    global _engine
    _engine = engine
