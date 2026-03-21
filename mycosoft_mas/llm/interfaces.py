from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request.
        """

    @abstractmethod
    async def embed(self, text: Union[str, List[str]], model: str) -> List[List[float]]:
        """
        Generate embeddings for text.
        """
