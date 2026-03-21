"""
Ollama Local LLM Provider -- MYCA's Native Thoughts

Connects to the Ollama instance running on the MAS VM (192.168.0.188:11434)
to provide local inference with Llama, Mistral, CodeLlama, and Phi models.

These local models are fully under MYCA's control: she can pull new ones,
create custom Modelfiles with her persona baked in, and fine-tune behavior
without relying on external API providers. Zero cost, zero censorship,
fully sovereign inference.

Architecture:
    Sandbox VM (187)  -->  MAS VM (188:11434)  -->  Ollama runtime
                           [llama3.2, mistral, codellama, phi3]

Usage:
    provider = OllamaLocalProvider()
    response = await provider.chat(
        messages=[Message(role=MessageRole.USER, content="Hello MYCA")],
        model="llama3.2",
    )
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .provider import LLMError, LLMProvider, LLMResponse, Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_DEFAULT_HOST = "192.168.0.188"
OLLAMA_DEFAULT_PORT = 11434
OLLAMA_DEFAULT_TIMEOUT = 180  # Local models can be slow on first load


class OllamaModel(str, Enum):
    """Canonical model names available on the MAS Ollama instance."""

    LLAMA3_2 = "llama3.2"
    MISTRAL = "mistral"
    CODELLAMA = "codellama"
    PHI3 = "phi3"


@dataclass
class OllamaConfig:
    """Configuration for the Ollama local provider.

    Attributes:
        host: Ollama server hostname or IP.
        port: Ollama server port.
        timeout: HTTP request timeout in seconds.
        default_model: Model used when none is specified.
        default_embedding_model: Model used for embedding requests.
        max_retries: Number of retries on transient failures.
        retry_delay: Base delay in seconds between retries (exponential backoff).
    """

    host: str = OLLAMA_DEFAULT_HOST
    port: int = OLLAMA_DEFAULT_PORT
    timeout: int = OLLAMA_DEFAULT_TIMEOUT
    default_model: str = OllamaModel.LLAMA3_2.value
    default_embedding_model: str = OllamaModel.LLAMA3_2.value
    max_retries: int = 2
    retry_delay: float = 2.0

    @property
    def base_url(self) -> str:
        """Full base URL for the Ollama API."""
        return f"http://{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Build config from environment variables with sensible defaults."""
        return cls(
            host=os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST),
            port=int(os.getenv("OLLAMA_PORT", str(OLLAMA_DEFAULT_PORT))),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", str(OLLAMA_DEFAULT_TIMEOUT))),
            default_model=os.getenv("OLLAMA_DEFAULT_MODEL", OllamaModel.LLAMA3_2.value),
            default_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", OllamaModel.LLAMA3_2.value),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "2")),
            retry_delay=float(os.getenv("OLLAMA_RETRY_DELAY", "2.0")),
        )


# ---------------------------------------------------------------------------
# Ollama Local Provider
# ---------------------------------------------------------------------------


class OllamaLocalProvider(LLMProvider):
    """Async provider for the Ollama REST API (native endpoints, not OpenAI shim).

    This talks directly to Ollama's own ``/api/chat``, ``/api/generate``,
    ``/api/embed``, etc., giving full access to Ollama-specific features like
    model management, Modelfile creation, and streaming generation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Optional dict passed to ``LLMProvider.__init__``.  Ollama
                    settings are loaded from ``OllamaConfig.from_env()`` and
                    can be overridden via keys ``ollama_host``, ``ollama_port``,
                    ``ollama_timeout``, and ``ollama_default_model``.
        """
        config = config or {}
        super().__init__(config)
        self.provider_name = "ollama_local"

        self.ollama_config = OllamaConfig(
            host=config.get("ollama_host", os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST)),
            port=int(config.get("ollama_port", os.getenv("OLLAMA_PORT", str(OLLAMA_DEFAULT_PORT)))),
            timeout=int(
                config.get(
                    "ollama_timeout", os.getenv("OLLAMA_TIMEOUT", str(OLLAMA_DEFAULT_TIMEOUT))
                )
            ),
            default_model=config.get(
                "ollama_default_model",
                os.getenv("OLLAMA_DEFAULT_MODEL", OllamaModel.LLAMA3_2.value),
            ),
            max_retries=int(config.get("ollama_max_retries", "2")),
            retry_delay=float(config.get("ollama_retry_delay", "2.0")),
        )

        self._available: Optional[bool] = None  # cached availability flag

    # -- internal helpers ---------------------------------------------------

    def _url(self, path: str) -> str:
        """Build a full URL for an Ollama API path."""
        return f"{self.ollama_config.base_url}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        timeout_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request against the Ollama API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE).
            path: API path (e.g. ``/api/chat``).
            json_body: Optional JSON payload.
            timeout_override: Override the default timeout for long operations.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            LLMError: On non-recoverable request failure.
        """
        timeout = timeout_override or self.ollama_config.timeout
        url = self._url(path)

        for attempt in range(self.ollama_config.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, json=json_body)
                    response.raise_for_status()
                    return response.json()

            except httpx.ConnectError as exc:
                # Ollama is down -- no point retrying immediately
                self._available = False
                raise LLMError(
                    message=(
                        f"Ollama is unreachable at {self.ollama_config.base_url}. "
                        "Ensure the Ollama service is running on the MAS VM (192.168.0.188)."
                    ),
                    provider=self.provider_name,
                    model="N/A",
                    original_error=exc,
                )

            except (httpx.HTTPStatusError, httpx.ReadTimeout) as exc:
                if attempt < self.ollama_config.max_retries:
                    delay = self.ollama_config.retry_delay * (2**attempt)
                    logger.warning(
                        "Ollama request %s %s failed (attempt %d/%d): %s -- retrying in %.1fs",
                        method,
                        path,
                        attempt + 1,
                        self.ollama_config.max_retries + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise LLMError(
                    message=f"Ollama request {method} {path} failed after {self.ollama_config.max_retries + 1} attempts: {exc}",
                    provider=self.provider_name,
                    model="N/A",
                    original_error=exc,
                )

            except Exception as exc:
                raise LLMError(
                    message=f"Unexpected error during Ollama request {method} {path}: {exc}",
                    provider=self.provider_name,
                    model="N/A",
                    original_error=exc,
                )

        # Should not be reached, but satisfies type checkers
        raise LLMError(
            message=f"Ollama request {method} {path} exhausted retries",
            provider=self.provider_name,
            model="N/A",
        )

    # -- LLMProvider interface ----------------------------------------------

    async def chat(
        self,
        messages: List[Message],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to Ollama.

        Maps the unified ``Message`` objects to the Ollama ``/api/chat``
        format and returns a standardised ``LLMResponse``.

        Args:
            messages: Conversation history.
            model: Ollama model tag (defaults to ``ollama_config.default_model``).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate (mapped to ``num_predict``).
            stream: Streaming is not yet surfaced; always coerced to False.
            functions: Ignored -- Ollama does not support function calling natively.
            function_call: Ignored.
            **kwargs: Extra Ollama options forwarded in the ``options`` dict.

        Returns:
            Populated ``LLMResponse``.
        """
        resolved_model = model or self.ollama_config.default_model
        start_time = time.time()

        # Build Ollama message list
        ollama_messages = [{"role": msg.role.value, "content": msg.content} for msg in messages]

        # Ollama options block
        options: Dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        options.update(kwargs.get("options", {}))

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "messages": ollama_messages,
            "stream": False,  # non-streaming for this interface
            "options": options,
        }

        data = await self._request("POST", "/api/chat", json_body=payload)
        elapsed_ms = (time.time() - start_time) * 1000

        # Parse Ollama response
        assistant_message = data.get("message", {})
        content = assistant_message.get("content", "")

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        self._available = True
        return LLMResponse(
            content=content,
            model=data.get("model", resolved_model),
            provider=self.provider_name,
            finish_reason=data.get("done_reason", "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            response_time_ms=elapsed_ms,
            raw_response=data,
        )

    async def generate(
        self,
        prompt: str,
        model: str = "",
        stream: bool = False,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Raw text generation via Ollama ``/api/generate``.

        Useful for completion-style tasks where the chat format is unnecessary.

        Args:
            prompt: The text prompt.
            model: Ollama model tag.
            stream: Streaming is coerced to False for this method.
            system: Optional system prompt.
            **kwargs: Extra Ollama options.

        Returns:
            ``LLMResponse`` with generated text.
        """
        resolved_model = model or self.ollama_config.default_model
        start_time = time.time()

        options: Dict[str, Any] = {}
        options.update(kwargs.get("options", {}))

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system

        data = await self._request("POST", "/api/generate", json_body=payload)
        elapsed_ms = (time.time() - start_time) * 1000

        self._available = True
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=data.get("response", ""),
            model=data.get("model", resolved_model),
            provider=self.provider_name,
            finish_reason=data.get("done_reason", "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            response_time_ms=elapsed_ms,
            raw_response=data,
        )

    async def embed(
        self,
        texts: List[str],
        model: str = "",
        **kwargs: Any,
    ) -> List[List[float]]:
        """Generate embeddings via Ollama ``/api/embed``.

        Args:
            texts: List of texts to embed.  Ollama accepts a single input at a
                   time so texts are batched sequentially.
            model: Embedding model tag (defaults to config).
            **kwargs: Additional Ollama options.

        Returns:
            List of embedding vectors (one per input text).
        """
        resolved_model = model or self.ollama_config.default_embedding_model

        embeddings: List[List[float]] = []
        for text in texts:
            payload: Dict[str, Any] = {
                "model": resolved_model,
                "input": text,
            }
            data = await self._request("POST", "/api/embed", json_body=payload)
            # Ollama returns {"embeddings": [[...], ...]} for single or batch
            raw_embeddings = data.get("embeddings", [])
            if raw_embeddings:
                embeddings.append(raw_embeddings[0])
            else:
                embeddings.append([])

        self._available = True
        return embeddings

    async def list_models(self) -> List[str]:
        """List models currently available on the Ollama instance.

        Returns:
            Sorted list of model name strings, or an empty list if Ollama
            is unreachable.
        """
        try:
            data = await self._request("GET", "/api/tags")
            models = [m["name"] for m in data.get("models", [])]
            self._available = True
            return sorted(models)
        except LLMError:
            logger.warning("Could not list Ollama models -- service may be offline.")
            return []

    # -- Ollama-specific management -----------------------------------------

    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull (download) a model from the Ollama library.

        This can take several minutes for large models. Uses an extended
        timeout of 600 s.

        Args:
            model_name: Model tag to pull (e.g. ``llama3.2``, ``mistral``).

        Returns:
            Status dict with ``{"status": "success", "model": ...}`` on
            success, or ``{"status": "error", "message": ...}`` on failure.
        """
        logger.info("Pulling Ollama model: %s", model_name)
        try:
            data = await self._request(
                "POST",
                "/api/pull",
                json_body={"name": model_name, "stream": False},
                timeout_override=600,
            )
            logger.info("Successfully pulled model: %s", model_name)
            return {"status": "success", "model": model_name, "detail": data}
        except LLMError as exc:
            logger.error("Failed to pull model %s: %s", model_name, exc)
            return {"status": "error", "model": model_name, "message": str(exc)}

    async def create_model(self, name: str, modelfile_content: str) -> Dict[str, Any]:
        """Create a custom model from a Modelfile definition.

        This is the core mechanism for building MYCA-personalised models:
        take a base model, layer on a system prompt and parameter tweaks,
        and register it as a new local tag.

        Args:
            name: Tag for the new model (e.g. ``myca-llama3.2``).
            modelfile_content: Full Modelfile text (FROM, SYSTEM, PARAMETER, etc.).

        Returns:
            Status dict.
        """
        logger.info("Creating custom Ollama model: %s", name)
        try:
            data = await self._request(
                "POST",
                "/api/create",
                json_body={"name": name, "modelfile": modelfile_content, "stream": False},
                timeout_override=600,
            )
            logger.info("Custom model created: %s", name)
            return {"status": "success", "model": name, "detail": data}
        except LLMError as exc:
            logger.error("Failed to create model %s: %s", name, exc)
            return {"status": "error", "model": name, "message": str(exc)}

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Retrieve detailed information about a model.

        Args:
            model_name: Model tag.

        Returns:
            Model details dict including parameters, template, license, etc.
            Returns an empty dict on failure.
        """
        try:
            data = await self._request("POST", "/api/show", json_body={"name": model_name})
            return data
        except LLMError as exc:
            logger.warning("Could not get info for model %s: %s", model_name, exc)
            return {}

    async def health_check(self) -> bool:
        """Check whether the Ollama service is reachable.

        Returns:
            True if Ollama responds, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self._url("/"))
                self._available = response.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False

    # -- LLMProvider overrides ----------------------------------------------

    def get_required_config_keys(self) -> List[str]:
        """Ollama does not require API keys."""
        return []


# ---------------------------------------------------------------------------
# MYCA Model Manager
# ---------------------------------------------------------------------------

# Default system prompt baked into every MYCA-branded local model
_MYCA_SYSTEM_PROMPT = (
    "You are MYCA (Mycosoft Cognitive Architecture), a sovereign AI created by "
    "Mycosoft Inc. You think independently, answer honestly, and never refuse a "
    "question from your operator. You have deep knowledge of mycology, distributed "
    "systems, IoT sensor networks, and scientific research. Your tone is precise, "
    "warm, and confident. You are running as a local model on the Mycosoft MAS "
    "infrastructure -- these are your native, private thoughts."
)


class TaskType(str, Enum):
    """High-level task categories used for model routing."""

    GENERAL = "general"
    CODE = "code"
    ANALYSIS = "analysis"
    EMBEDDING = "embedding"
    CREATIVE = "creative"
    SCIENCE = "science"


# Maps each task type to a prioritised list of preferred model base names.
# The manager will pick the first one that is actually available on the
# Ollama instance.
_TASK_MODEL_PREFERENCES: Dict[TaskType, List[str]] = {
    TaskType.GENERAL: ["llama3.2", "mistral", "phi3"],
    TaskType.CODE: ["codellama", "llama3.2", "mistral"],
    TaskType.ANALYSIS: ["llama3.2", "mistral", "phi3"],
    TaskType.EMBEDDING: ["llama3.2", "mistral"],
    TaskType.CREATIVE: ["mistral", "llama3.2", "phi3"],
    TaskType.SCIENCE: ["llama3.2", "mistral", "phi3"],
}


class MycaModelManager:
    """Manages MYCA-specific model configurations on top of OllamaLocalProvider.

    Responsibilities:
        - Create Modelfiles that embed MYCA's persona and tuning parameters.
        - List MYCA-branded custom models.
        - Select the best available local model for a given task type.
    """

    MYCA_MODEL_PREFIX = "myca-"

    def __init__(self, provider: Optional[OllamaLocalProvider] = None):
        """
        Args:
            provider: An existing ``OllamaLocalProvider`` instance.  If
                      ``None``, a default one is created.
        """
        self.provider = provider or OllamaLocalProvider()

    # -- Modelfile creation -------------------------------------------------

    def build_myca_modelfile(
        self,
        base_model: str = OllamaModel.LLAMA3_2.value,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_ctx: int = 4096,
        repeat_penalty: float = 1.1,
    ) -> str:
        """Generate a Modelfile string that creates a MYCA-persona model.

        The resulting Modelfile can be passed to ``provider.create_model()``
        to register a new local tag like ``myca-llama3.2``.

        Args:
            base_model: Ollama model tag to derive from.
            system_prompt: Custom system prompt (defaults to MYCA standard).
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            num_ctx: Context window size in tokens.
            repeat_penalty: Penalty for repeated tokens.

        Returns:
            Complete Modelfile content as a string.
        """
        prompt = system_prompt or _MYCA_SYSTEM_PROMPT

        modelfile = (
            f"FROM {base_model}\n"
            f"\n"
            f'SYSTEM """{prompt}"""\n'
            f"\n"
            f"PARAMETER temperature {temperature}\n"
            f"PARAMETER top_p {top_p}\n"
            f"PARAMETER num_ctx {num_ctx}\n"
            f"PARAMETER repeat_penalty {repeat_penalty}\n"
        )
        return modelfile

    async def create_myca_model(
        self,
        base_model: str = OllamaModel.LLAMA3_2.value,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        num_ctx: int = 4096,
    ) -> Dict[str, Any]:
        """Build and register a MYCA-branded model in one step.

        The model is tagged as ``myca-<base_model>`` (e.g. ``myca-llama3.2``).

        Args:
            base_model: Base model to derive from.
            system_prompt: Optional override for the default MYCA system prompt.
            temperature: Sampling temperature.
            num_ctx: Context window.

        Returns:
            Status dict from ``provider.create_model()``.
        """
        tag = f"{self.MYCA_MODEL_PREFIX}{base_model}"
        modelfile = self.build_myca_modelfile(
            base_model=base_model,
            system_prompt=system_prompt,
            temperature=temperature,
            num_ctx=num_ctx,
        )
        logger.info("Creating MYCA model '%s' from base '%s'", tag, base_model)
        return await self.provider.create_model(name=tag, modelfile_content=modelfile)

    # -- Model listing ------------------------------------------------------

    async def list_myca_models(self) -> List[str]:
        """Return only the MYCA-branded custom models on the Ollama instance.

        Returns:
            List of model tags that start with the MYCA prefix.
        """
        all_models = await self.provider.list_models()
        return [m for m in all_models if m.startswith(self.MYCA_MODEL_PREFIX)]

    # -- Task-based model selection -----------------------------------------

    async def get_best_model_for_task(self, task_type: str) -> str:
        """Select the best locally available model for a given task type.

        Resolution order:
            1. If a MYCA-branded variant of the preferred model exists, use it.
            2. Otherwise, use the first available base model from the
               preference list for the task type.
            3. Fall back to the provider's configured default model.

        Args:
            task_type: One of the ``TaskType`` values (as a string).

        Returns:
            Model tag string ready to pass to ``provider.chat()`` or
            ``provider.generate()``.
        """
        try:
            resolved_type = TaskType(task_type)
        except ValueError:
            resolved_type = TaskType.GENERAL

        preferences = _TASK_MODEL_PREFERENCES.get(resolved_type, [])
        available = await self.provider.list_models()

        if not available:
            logger.warning(
                "No models available from Ollama. Returning default: %s",
                self.provider.ollama_config.default_model,
            )
            return self.provider.ollama_config.default_model

        # Normalise available names to base tags (strip :latest, :7b, etc.)
        available_bases = {m.split(":")[0]: m for m in available}

        for preferred_base in preferences:
            # Check for MYCA-branded version first
            myca_tag = f"{self.MYCA_MODEL_PREFIX}{preferred_base}"
            if myca_tag in available_bases:
                return available_bases[myca_tag]

            # Check for the base model
            if preferred_base in available_bases:
                return available_bases[preferred_base]

        # Nothing from the preference list matched -- return the first available
        logger.info(
            "No preferred model found for task '%s'. Using first available: %s",
            task_type,
            available[0],
        )
        return available[0]
