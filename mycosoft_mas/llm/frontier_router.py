"""
MYCA Frontier LLM Router

Routes requests to frontier LLMs (Gemini, Claude, GPT-4) for intelligent responses.
This is the "brain" of MYCA - all voice queries go through here before PersonaPlex speaks.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from mycosoft_mas.llm.error_sanitizer import sanitize_for_log, sanitize_error_body

logger = logging.getLogger(__name__)


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
    Routes MYCA requests to LLMs with her own local brain as primary.

    Priority order (local-first — MYCA is sovereign):
    1. Ollama (local — runs on MAS VM, MYCA's own brain)
    2. Gemini (cloud fallback)
    3. Claude (cloud fallback)
    4. GPT-4 (cloud fallback)

    Router mode controlled by LLM_ROUTER_MODE env var:
    - "local_first" (default): Ollama primary, cloud fallback
    - "ollama_only": Ollama only, no cloud calls
    - "cloud_first": Cloud primary, Ollama fallback (legacy)
    - "hybrid": Intelligent selection based on task
    """

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Ollama — MYCA's own local brain (runs on MAS VM 192.168.0.188:11434)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://192.168.0.188:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

        # Router mode: local_first | ollama_only | cloud_first | hybrid
        self.router_mode = os.getenv("LLM_ROUTER_MODE", "local_first")

        self.persona_path = os.path.join(
            os.path.dirname(__file__),
            "../../config/myca_full_persona.txt"
        )
        self.persona = self._load_persona()

        # Provider health tracking
        self.provider_health = {
            "ollama": {"healthy": True, "failures": 0},
            "gemini": {"healthy": True, "failures": 0},
            "claude": {"healthy": True, "failures": 0},
            "openai": {"healthy": True, "failures": 0},
        }

        configured = [f"ollama({self.ollama_base_url}, model={self.ollama_model})"]
        if self.gemini_api_key:
            configured.append("gemini")
        if self.anthropic_api_key:
            configured.append("claude")
        if self.openai_api_key:
            configured.append("openai")

        logger.info(
            "[MYCA Brain] FrontierLLMRouter initialized. Mode: %s. Providers: %s. Persona: %d chars",
            self.router_mode, ", ".join(configured), len(self.persona),
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
    
    def _build_system_prompt(self, context: ConversationContext, tools: Optional[List[Dict]] = None) -> str:
        """Build the full system prompt with persona and context."""
        prompt_parts = [
            self.persona,
            "",
            f"=== CURRENT SESSION ===",
            f"Session ID: {context.session_id}",
            f"User: {context.user_id}",
            f"Turn: {context.turn_count}",
            f"Active Role: {context.current_role}",
            f"Timestamp: {datetime.now().isoformat()}",
        ]
        
        if context.active_tools:
            prompt_parts.extend([
                "",
                f"=== AVAILABLE TOOLS ===",
                ", ".join(context.active_tools)
            ])
        
        if tools:
            prompt_parts.extend([
                "",
                f"=== TOOL DEFINITIONS ===",
            ])
            for tool in tools:
                prompt_parts.append(f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}")
        
        return "\n".join(prompt_parts)
    
    def _build_messages(
        self, 
        user_message: str, 
        context: ConversationContext,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build message list for LLM."""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 turns max)
        for msg in context.history[-20:]:
            messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def stream_response(
        self,
        message: str,
        context: ConversationContext,
        tools: Optional[List[Dict]] = None,
        provider: str = "auto"
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from frontier LLM.
        
        Args:
            message: User message
            context: Conversation context
            tools: Available tools for function calling
            provider: "auto", "gemini", "claude", or "openai"
        
        Yields:
            Response tokens as they arrive
        """
        system_prompt = self._build_system_prompt(context, tools)
        messages = self._build_messages(message, context, system_prompt)
        
        # Auto-select provider based on health and availability
        if provider == "auto":
            provider = self._select_provider()
        
        logger.info(f"[MYCA Brain] Using {provider} for: {message[:50]}...")
        
        yielded = 0
        try:
            if provider == "ollama":
                async for token in self._stream_ollama(messages):
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
                # No provider matched — always try Ollama as safety net
                logger.warning("[MYCA Brain] Provider %s not available, trying Ollama at %s", provider, self.ollama_base_url)
                async for token in self._stream_ollama(messages):
                    yielded += 1
                    yield token

            if yielded == 0:
                logger.warning("[MYCA Brain] Provider %s returned no tokens", provider)
                yield LLM_FALLBACK_MESSAGE

        except Exception as e:
            logger.error(f"[MYCA Brain] Error with {provider}: {sanitize_for_log(e)}")
            self._mark_provider_failure(provider)
            yield LLM_FALLBACK_MESSAGE
    
    def _select_provider(self) -> str:
        """Select best available provider based on router mode.

        Modes:
        - local_first: Ollama primary, cloud only if Ollama fails
        - ollama_only: Never use cloud providers
        - cloud_first: Cloud primary, Ollama fallback (legacy)
        - hybrid: Try Ollama first, but fall back to cloud freely
        """
        if self.router_mode == "ollama_only":
            return "ollama"

        if self.router_mode == "cloud_first":
            # Legacy mode — cloud first, Ollama last
            if self.gemini_api_key and self.provider_health["gemini"]["healthy"]:
                return "gemini"
            if self.anthropic_api_key and self.provider_health["claude"]["healthy"]:
                return "claude"
            if self.openai_api_key and self.provider_health["openai"]["healthy"]:
                return "openai"
            if self.provider_health["ollama"]["healthy"]:
                return "ollama"
            return "gemini"

        # local_first (default) and hybrid — Ollama is primary
        if self.provider_health["ollama"]["healthy"]:
            return "ollama"
        # Cloud fallback only when Ollama is down
        if self.gemini_api_key and self.provider_health["gemini"]["healthy"]:
            return "gemini"
        if self.anthropic_api_key and self.provider_health["claude"]["healthy"]:
            return "claude"
        if self.openai_api_key and self.provider_health["openai"]["healthy"]:
            return "openai"
        # Everything failed — still try Ollama (it might recover)
        return "ollama"
    
    def _mark_provider_failure(self, provider: str):
        """Mark a provider as having failed."""
        if provider in self.provider_health:
            self.provider_health[provider]["failures"] += 1
            if self.provider_health[provider]["failures"] >= 3:
                self.provider_health[provider]["healthy"] = False
    
    async def _stream_gemini(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from Gemini with fast failure."""
        import httpx
        import json
        
        # Convert messages to Gemini format
        contents = []
        system_instruction = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
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
                        logger.error(f"Gemini API error {response.status_code}: {sanitize_error_body(body)}")
                        self._mark_provider_failure("gemini")
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if "error" in data:
                                    err = data["error"]
                                    err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                                    logger.error(f"Gemini error: {sanitize_for_log(Exception(err_msg))}")
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
        import httpx
        import json
        
        # Convert to Claude format
        claude_messages = [m for m in messages if m["role"] != "system"]
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "system": system,
            "messages": claude_messages,
            "stream": True
        }
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                ) as response:
                    # Check for error status codes immediately
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(f"Claude API error {response.status_code}: {sanitize_error_body(body)}")
                        self._mark_provider_failure("claude")
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if data.get("type") == "error":
                                    err_msg = data.get("error", {}).get("message", str(data))
                                    logger.error(f"Claude error: {sanitize_for_log(Exception(err_msg))}")
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
        import httpx
        import json
        
        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "max_tokens": 2048,
            "stream": True
        }
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    # Check for error status codes immediately
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(f"OpenAI API error {response.status_code}: {sanitize_error_body(body)}")
                        self._mark_provider_failure("openai")
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                # Check for error response
                                if "error" in data:
                                    err = data["error"]
                                    err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                                    logger.error(f"OpenAI error: {sanitize_for_log(Exception(err_msg))}")
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

    async def _stream_ollama(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from Ollama (local LLM on MAS VM)."""
        import httpx
        import json

        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
        }

        url = f"{self.ollama_base_url}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(f"Ollama API error {response.status_code}: {sanitize_error_body(body)}")
                        self._mark_provider_failure("ollama")
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "error" in data:
                                logger.error(f"Ollama error: {data['error']}")
                                self._mark_provider_failure("ollama")
                                return
                            msg = data.get("message", {})
                            content = msg.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama stream error: {sanitize_for_log(e)}")
            self._mark_provider_failure("ollama")


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
