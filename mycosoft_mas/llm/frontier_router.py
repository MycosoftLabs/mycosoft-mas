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

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Context for MYCA conversation."""
    session_id: str
    conversation_id: str
    user_id: str = "morgan"
    turn_count: int = 0
    history: List[Dict[str, str]] = None
    active_tools: List[str] = None
    current_role: str = "orchestrator"
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
        if self.active_tools is None:
            self.active_tools = []


class FrontierLLMRouter:
    """
    Routes MYCA requests to frontier LLMs with full persona and context.
    
    Priority order:
    1. Gemini 2.5 Pro (default - best for conversation)
    2. Claude 3.5 Sonnet (fallback - best for reasoning)
    3. GPT-4 Turbo (fallback - best for tools)
    """
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.persona_path = os.path.join(
            os.path.dirname(__file__),
            "../../config/myca_full_persona.txt"
        )
        self.persona = self._load_persona()
        
        # Provider health tracking
        self.provider_health = {
            "gemini": {"healthy": True, "failures": 0},
            "claude": {"healthy": True, "failures": 0},
            "openai": {"healthy": True, "failures": 0},
        }
        
        logger.info(f"FrontierLLMRouter initialized. Persona: {len(self.persona)} chars")
    
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
    
    def _build_system_prompt(self, context: ConversationContext, tools: List[Dict] = None) -> str:
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
        tools: List[Dict] = None,
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
        
        try:
            if provider == "gemini" and self.gemini_api_key:
                async for token in self._stream_gemini(messages):
                    yield token
            elif provider == "claude" and self.anthropic_api_key:
                async for token in self._stream_claude(messages, system_prompt):
                    yield token
            elif provider == "openai" and self.openai_api_key:
                async for token in self._stream_openai(messages):
                    yield token
            else:
                # Fallback to local response
                yield f"I apologize, but my connection to my main intelligence is currently unavailable. "
                yield f"Please try again in a moment."
                
        except Exception as e:
            logger.error(f"[MYCA Brain] Error with {provider}: {e}")
            self._mark_provider_failure(provider)
            yield f"I encountered an issue processing your request. Let me try again."
    
    def _select_provider(self) -> str:
        """Select best available provider."""
        if self.gemini_api_key and self.provider_health["gemini"]["healthy"]:
            return "gemini"
        if self.anthropic_api_key and self.provider_health["claude"]["healthy"]:
            return "claude"
        if self.openai_api_key and self.provider_health["openai"]["healthy"]:
            return "openai"
        return "gemini"  # Default
    
    def _mark_provider_failure(self, provider: str):
        """Mark a provider as having failed."""
        if provider in self.provider_health:
            self.provider_health[provider]["failures"] += 1
            if self.provider_health[provider]["failures"] >= 3:
                self.provider_health[provider]["healthy"] = False
    
    async def _stream_gemini(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from Gemini."""
        import httpx
        
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
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={self.gemini_api_key}&alt=sse"
        
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        try:
                            data = json.loads(line[6:])
                            if "candidates" in data:
                                for candidate in data["candidates"]:
                                    if "content" in candidate:
                                        for part in candidate["content"].get("parts", []):
                                            if "text" in part:
                                                yield part["text"]
                        except json.JSONDecodeError:
                            continue
    
    async def _stream_claude(self, messages: List[Dict], system: str) -> AsyncGenerator[str, None]:
        """Stream from Claude."""
        import httpx
        
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
        
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if "text" in delta:
                                    yield delta["text"]
                        except json.JSONDecodeError:
                            continue
    
    async def _stream_openai(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream from OpenAI."""
        import httpx
        
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
        
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        try:
                            data = json.loads(line[6:])
                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue


# Singleton instance
_frontier_router: Optional[FrontierLLMRouter] = None


def get_frontier_router() -> FrontierLLMRouter:
    """Get or create the frontier router singleton."""
    global _frontier_router
    if _frontier_router is None:
        _frontier_router = FrontierLLMRouter()
    return _frontier_router
