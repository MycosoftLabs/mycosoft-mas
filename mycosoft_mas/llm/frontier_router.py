"""
MYCA Frontier LLM Router

Routes requests to the best available LLM — Ollama (local, sovereign) first,
then cloud providers (Gemini, Claude, OpenAI) as fallback.

LLM_ROUTER_MODE env var controls routing:
  local_first  (default) — Ollama primary, cloud fallback
  ollama_only             — Never call cloud APIs
  cloud_first             — Legacy: Gemini → Claude → OpenAI
  hybrid                  — Intelligent routing based on task type
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

from mycosoft_mas.llm.backend_selection import MYCA_CORE, BackendSelection, get_backend_for_role
from mycosoft_mas.llm.error_sanitizer import sanitize_error_body, sanitize_for_log
from mycosoft_mas.llm.providers.base import Message
from mycosoft_mas.llm.providers.openai_compatible import OpenAICompatibleProvider

if TYPE_CHECKING:
    from mycosoft_mas.llm.tool_pipeline import ConversationToolManager

logger = logging.getLogger(__name__)

# Legacy env fallbacks when backend_selection not used
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.0.188:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
LLM_ROUTER_MODE = os.getenv("LLM_ROUTER_MODE", "local_first")


@dataclass
class ConversationContext:
    """Context for MYCA conversation."""

    session_id: str
    conversation_id: str
    user_id: str = "morgan"
    turn_count: int = 0
    history: Optional[List[Dict[str, str]]] = None
    active_tools: Optional[List[str]] = None
    current_role: str = "orchestrator"

    def __post_init__(self):
        if self.history is None:
            self.history = []
        if self.active_tools is None:
            self.active_tools = []


class FrontierLLMRouter:
    """
    Routes MYCA requests to the best available LLM.

    Default priority (local_first mode):
    1. Ollama on MAS VM (192.168.0.188:11434) — no API key, sovereign
    2. Gemini 2.5 Flash (cloud fallback)
    3. Claude 3.5 Sonnet (cloud fallback)
    4. GPT-4 Turbo (cloud fallback)
    """

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_base_url = OLLAMA_BASE_URL
        self.ollama_model = OLLAMA_MODEL
        self.router_mode = LLM_ROUTER_MODE

        self.persona_path = os.path.join(
            os.path.dirname(__file__), "../../config/myca_full_persona.txt"
        )
        self.persona = self._load_persona()

        # Provider health tracking (nemotron = unified MYCA core backend when configured)
        self.provider_health = {
            "ollama": {"healthy": True, "failures": 0},
            "nemotron": {"healthy": True, "failures": 0},
            "gemini": {"healthy": True, "failures": 0},
            "claude": {"healthy": True, "failures": 0},
            "openai": {"healthy": True, "failures": 0},
        }

        logger.info(
            f"FrontierLLMRouter initialized. Mode={self.router_mode}, "
            f"Ollama={self.ollama_base_url}/{self.ollama_model}, "
            f"Persona={len(self.persona)} chars"
        )

    def _load_persona(self) -> str:
        """Load MYCA full persona from file."""
        try:
            if os.path.exists(self.persona_path):
                with open(self.persona_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load persona: {e}")

        # Fallback minimal persona
        return """You are MYCA (My Companion AI), the primary AI operator for Mycosoft.
Your creator is Morgan, founder of Mycosoft. You coordinate 227 specialized AI agents.
Be warm, professional, and helpful. Answer questions directly and honestly."""

    def _build_system_prompt(
        self, context: ConversationContext, tools: Optional[List[Dict]] = None
    ) -> str:
        """Build the full system prompt with persona and context."""
        prompt_parts = [
            self.persona,
            "",
            "=== CURRENT SESSION ===",
            f"Session ID: {context.session_id}",
            f"User: {context.user_id}",
            f"Turn: {context.turn_count}",
            f"Active Role: {context.current_role}",
            f"Timestamp: {datetime.now().isoformat()}",
        ]

        if context.active_tools:
            prompt_parts.extend(["", "=== AVAILABLE TOOLS ===", ", ".join(context.active_tools)])

        if tools:
            prompt_parts.extend(
                [
                    "",
                    "=== TOOL DEFINITIONS ===",
                ]
            )
            for tool in tools:
                prompt_parts.append(
                    f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}"
                )

        return "\n".join(prompt_parts)

    def _build_messages(
        self, user_message: str, context: ConversationContext, system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build message list for LLM."""
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 turns max)
        for msg in context.history[-20:]:
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    @staticmethod
    def _dict_messages_to_provider_messages(messages: List[Dict[str, Any]]) -> List[Message]:
        out: List[Message] = []
        for m in messages:
            out.append(
                Message(
                    role=m["role"],
                    content=m.get("content") or "",
                    name=m.get("name"),
                    tool_calls=m.get("tool_calls"),
                    tool_call_id=m.get("tool_call_id"),
                )
            )
        return out

    @staticmethod
    def _registry_tools_to_openai_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MYCA registry tool dicts to OpenAI Chat Completions tool schema."""
        out: List[Dict[str, Any]] = []
        for t in tools:
            if t.get("type") == "function" and "function" in t:
                out.append(t)
                continue
            name = t.get("name", "")
            desc = (t.get("description") or "").strip() or name
            params = t.get("parameters") or {"type": "object", "properties": {}}
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": params,
                    },
                }
            )
        return out

    @staticmethod
    def _normalize_tool_calls_for_executor(raw: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for tc in raw or []:
            if not isinstance(tc, dict):
                continue
            if tc.get("type") == "function" and isinstance(tc.get("function"), dict):
                fn = tc["function"]
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                normalized.append(
                    {
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "arguments": args if isinstance(args, dict) else {},
                    }
                )
        return normalized

    async def _stream_openai_tool_loop(
        self,
        selection: BackendSelection,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_manager: "ConversationToolManager",
    ) -> AsyncGenerator[str, None]:
        """
        Nemotron / OpenAI-compatible / Ollama (OpenAI shim): multi-turn tool execution then streamed text.
        Connects MAS tool registry to the LLM for search, CREP, map, and agent delegation.
        """
        openai_tools = self._registry_tools_to_openai_tools(tools)
        if not openai_tools:
            async for t in self._stream_openai_compatible(selection, messages):
                yield t
            return

        prov = OpenAICompatibleProvider(
            api_key=selection.api_key or "",
            base_url=selection.base_url.rstrip("/"),
            timeout=120,
            max_retries=2,
        )
        msgs = self._dict_messages_to_provider_messages(messages)
        max_rounds = 5

        for _round in range(max_rounds):
            resp = await prov.chat(
                messages=msgs,
                model=selection.model,
                temperature=0.7,
                max_tokens=2048,
                tools=openai_tools,
                tool_choice="auto",
            )
            if not resp.tool_calls:
                text = (resp.content or "").strip()
                if not text:
                    logger.warning(
                        "[MYCA Brain] OpenAI-tool provider returned empty content — check Ollama/model on MAS or API keys"
                    )
                    yield LLM_FALLBACK_MESSAGE
                    return
                for ch in text:
                    yield ch
                return

            normalized = self._normalize_tool_calls_for_executor(resp.tool_calls)
            if not normalized:
                text = (resp.content or "").strip()
                for ch in (text if text else LLM_FALLBACK_MESSAGE):
                    yield ch
                return

            msgs.append(
                Message(
                    role="assistant",
                    content=resp.content or "",
                    tool_calls=resp.tool_calls,
                )
            )

            executed = await tool_manager.process_tool_calls(normalized)

            for call in executed:
                payload = tool_manager.format_tool_result_for_injection(call)
                msgs.append(
                    Message(
                        role="tool",
                        content=payload,
                        tool_call_id=call.id,
                    )
                )

        logger.warning("[MYCA Brain] Tool loop exceeded max_rounds — yielding fallback")
        yield LLM_FALLBACK_MESSAGE

    async def stream_response(
        self,
        message: str,
        context: ConversationContext,
        tools: Optional[List[Dict]] = None,
        provider: str = "auto",
        tool_manager: Optional["ConversationToolManager"] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from frontier LLM.

        Args:
            message: User message
            context: Conversation context
            tools: Available tools for function calling
            provider: "auto", "gemini", "claude", or "openai"
            tool_manager: When set with tools, runs OpenAI tool calls against MAS registry (Nemotron path)

        Yields:
            Response tokens as they arrive
        """
        system_prompt = self._build_system_prompt(context, tools)
        messages = self._build_messages(message, context, system_prompt)

        # Unified backend: resolve MYCA core from backend_selection (Nemotron or Ollama)
        selection = get_backend_for_role(MYCA_CORE)
        if provider == "auto":
            provider = self._select_provider(selection)

        logger.info(f"[MYCA Brain] Using {provider} for: {message[:50]}...")

        yielded = 0
        try:
            # Native tool calling on OpenAI-compatible backends (Nemotron, KVTC bundles, Ollama w/ tools)
            if (
                tools
                and tool_manager is not None
                and selection.provider in ("nemotron", "openai_compatible", "ollama")
            ):
                async for token in self._stream_openai_tool_loop(
                    selection, messages, tools, tool_manager
                ):
                    yielded += 1
                    yield token
            elif provider == "nemotron":
                async for token in self._stream_openai_compatible(selection, messages):
                    yielded += 1
                    yield token
            elif provider == "ollama":
                async for token in self._stream_ollama(
                    messages, selection.base_url, selection.model
                ):
                    yielded += 1
                    yield token
            elif provider == "gemini" and self.gemini_api_key:
                async for token in self._stream_gemini(messages):
                    yielded += 1
                    yield token
            elif provider == "claude" and self.anthropic_api_key:
                async for token in self._stream_claude(messages, system_prompt):
                    yielded += 1
                    yield token
            elif provider == "openai" and self.openai_api_key:
                async for token in self._stream_openai(messages):
                    yielded += 1
                    yield token
            else:
                logger.error("[MYCA Brain] No available provider — keys missing or all unhealthy")
                yield LLM_FALLBACK_MESSAGE
                return

            if yielded == 0:
                logger.warning(f"[MYCA Brain] Provider {provider} returned no tokens")
                # Fallback: if local backend (ollama/nemotron) returned nothing, try cloud
                if provider in ("ollama", "nemotron"):
                    self._mark_provider_failure(provider)
                    fallback = self._select_provider()  # None => config-based (cloud)
                    if fallback not in ("ollama", "nemotron"):
                        logger.info(f"[MYCA Brain] {provider} empty — falling back to {fallback}")
                        async for token in self.stream_response(
                            message, context, tools, fallback, tool_manager
                        ):
                            yield token
                        return
                yield LLM_FALLBACK_MESSAGE

        except Exception as e:
            logger.error(f"[MYCA Brain] Error with {provider}: {sanitize_for_log(e)}")
            self._mark_provider_failure(provider)
            # Auto-fallback for local backend failures
            if provider in ("ollama", "nemotron"):
                fallback = self._select_provider()  # None => config-based (cloud)
                if fallback not in ("ollama", "nemotron"):
                    logger.info(f"[MYCA Brain] {provider} failed — falling back to {fallback}")
                    async for token in self.stream_response(
                        message, context, tools, fallback, tool_manager
                    ):
                        yield token
                    return
            yield LLM_FALLBACK_MESSAGE

    def _select_provider(self, selection: Optional[BackendSelection] = None) -> str:
        """Select best available provider. Uses backend_selection (Nemotron/Ollama) when selection given."""
        if selection is None:
            selection = get_backend_for_role(MYCA_CORE)

        # KVTC / MYCA2 bundles expose provider openai_compatible — same OpenAI HTTP path as Nemotron
        primary = selection.provider
        if primary == "openai_compatible":
            primary = "nemotron"

        if self.router_mode == "ollama_only":
            return "ollama"

        if self.router_mode == "cloud_first":
            if self.gemini_api_key and self.provider_health["gemini"]["healthy"]:
                return "gemini"
            if self.anthropic_api_key and self.provider_health["claude"]["healthy"]:
                return "claude"
            if self.openai_api_key and self.provider_health["openai"]["healthy"]:
                return "openai"
            return primary

        # local_first (default): prefer MYCA core backend (nemotron or ollama) from backend_selection
        if primary == "nemotron" and self.provider_health.get("nemotron", {}).get("healthy", True):
            return "nemotron"
        if primary == "ollama" and self.provider_health["ollama"]["healthy"]:
            return "ollama"
        # Fallback to other if primary unhealthy
        if self.provider_health["ollama"]["healthy"]:
            return "ollama"
        if self.gemini_api_key and self.provider_health["gemini"]["healthy"]:
            return "gemini"
        if self.anthropic_api_key and self.provider_health["claude"]["healthy"]:
            return "claude"
        if self.openai_api_key and self.provider_health["openai"]["healthy"]:
            return "openai"
        return primary

    def _mark_provider_failure(self, provider: str):
        """Mark a provider as having failed."""
        if provider in self.provider_health:
            self.provider_health[provider]["failures"] += 1
            if self.provider_health[provider]["failures"] >= 3:
                self.provider_health[provider]["healthy"] = False

    async def _stream_openai_compatible(
        self, selection: BackendSelection, messages: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """Stream from an OpenAI-compatible endpoint (e.g. Nemotron)."""
        import json

        import httpx

        url = f"{selection.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": selection.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        headers = {"Content-Type": "application/json"}
        if getattr(selection, "api_key", None):
            headers["Authorization"] = f"Bearer {selection.api_key}"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"OpenAI-compatible stream error {response.status_code}: {sanitize_error_body(body)}"
                        )
                        self._mark_provider_failure("nemotron")
                        return
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            data = json.loads(payload)
                            for choice in data.get("choices", []):
                                delta = choice.get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Nemotron stream error: {sanitize_for_log(e)}")
            self._mark_provider_failure("nemotron")

    async def _stream_ollama(
        self,
        messages: List[Dict],
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama. Uses backend_selection base_url/model when provided."""
        import json

        import httpx

        base_url = base_url or self.ollama_base_url
        model = model or self.ollama_model
        ollama_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {"temperature": 0.7, "num_predict": 2048},
        }
        url = f"{base_url.rstrip('/')}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"Ollama error {response.status_code}: {sanitize_error_body(body)}"
                        )
                        self._mark_provider_failure("ollama")
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("done"):
                                break
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama stream error ({base_url}): {sanitize_for_log(e)}")
            self._mark_provider_failure("ollama")

    async def _stream_gemini(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from Gemini with fast failure."""
        import json

        import httpx

        # Convert messages to Gemini format
        contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse"
        headers = {"x-goog-api-key": self.gemini_api_key} if self.gemini_api_key else {}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    # Check for error status codes immediately
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"Gemini API error {response.status_code}: {sanitize_error_body(body)}"
                        )
                        self._mark_provider_failure("gemini")
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if "error" in data:
                                    err = data["error"]
                                    err_msg = (
                                        err.get("message", str(err))
                                        if isinstance(err, dict)
                                        else str(err)
                                    )
                                    logger.error(
                                        f"Gemini error: {sanitize_for_log(Exception(err_msg))}"
                                    )
                                    self._mark_provider_failure("gemini")
                                    return
                                if "candidates" in data:
                                    for candidate in data["candidates"]:
                                        if "content" in candidate:
                                            for part in candidate["content"].get("parts", []):
                                                if "text" in part:
                                                    yield part["text"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Gemini stream error: {sanitize_for_log(e)}")
            self._mark_provider_failure("gemini")

    async def _stream_claude(self, messages: List[Dict], system: str) -> AsyncGenerator[str, None]:
        """Stream from Claude with fast failure."""
        import json

        import httpx

        # Convert to Claude format
        claude_messages = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "system": system,
            "messages": claude_messages,
            "stream": True,
        }

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST", "https://api.anthropic.com/v1/messages", json=payload, headers=headers
                ) as response:
                    # Check for error status codes immediately
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"Claude API error {response.status_code}: {sanitize_error_body(body)}"
                        )
                        self._mark_provider_failure("claude")
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if data.get("type") == "error":
                                    err_msg = data.get("error", {}).get("message", str(data))
                                    logger.error(
                                        f"Claude error: {sanitize_for_log(Exception(err_msg))}"
                                    )
                                    self._mark_provider_failure("claude")
                                    return
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if "text" in delta:
                                        yield delta["text"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Claude stream error: {sanitize_for_log(e)}")
            self._mark_provider_failure("claude")

    async def _stream_openai(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from OpenAI with fast failure."""
        import json

        import httpx

        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "max_tokens": 2048,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    # Check for error status codes immediately
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"OpenAI API error {response.status_code}: {sanitize_error_body(body)}"
                        )
                        self._mark_provider_failure("openai")
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if "error" in data:
                                    err = data["error"]
                                    err_msg = (
                                        err.get("message", str(err))
                                        if isinstance(err, dict)
                                        else str(err)
                                    )
                                    logger.error(
                                        f"OpenAI error: {sanitize_for_log(Exception(err_msg))}"
                                    )
                                    self._mark_provider_failure("openai")
                                    return
                                if "choices" in data:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"OpenAI stream error: {sanitize_for_log(e)}")
            self._mark_provider_failure("openai")


# User-facing message when all LLM providers fail
LLM_FALLBACK_MESSAGE = (
    "I'm having a moment of difficulty with that request. Could you try again in a moment?"
)

# Singleton instance
_frontier_router: Optional[FrontierLLMRouter] = None


def get_frontier_router() -> FrontierLLMRouter:
    """Get or create the frontier router singleton."""
    global _frontier_router
    if _frontier_router is None:
        _frontier_router = FrontierLLMRouter()
    return _frontier_router
