import os
import aiohttp
from typing import Dict, Any, List, Union
from .interfaces import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"OpenAI API error {resp.status}: {text}")
                return await resp.json()

    async def embed(self, text: Union[str, List[str]], model: str) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "input": text
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/embeddings", json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"OpenAI API error {resp.status}: {text}")
                data = await resp.json()
                return [item["embedding"] for item in data["data"]]

class OpenAICompatibleProvider(OpenAIProvider):
    """Generic provider for OpenAI-compatible APIs (LiteLLM, vLLM, Ollama)"""
    pass
