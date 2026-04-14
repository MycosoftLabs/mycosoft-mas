"""
Tool Pipeline — Streaming tool execution with cancellation.

Full-Duplex Consciousness OS (April 2026).

ToolExecutor runs tool calls with:
- Progressive progress updates (ToolProgress events)
- CancellationToken integration (stop mid-tool on barge-in)
- Timeout enforcement
- Speech integration helpers (speak while tools run)

Design principle: tools should never block the conversation.
MYCA can keep talking while tools are running, and announce
results as they arrive.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from mycosoft_mas.consciousness.cancellation import CancellationToken

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Status of a tool execution."""

    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class ToolProgress:
    """A single progress update from a running tool."""

    status: ToolStatus
    tool: str
    result: Optional[Any] = None
    error: Optional[str] = None
    progress_pct: float = 0.0  # 0.0–1.0
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def summary(self) -> str:
        """Human-readable summary for speech integration."""
        if self.status == ToolStatus.COMPLETED:
            if isinstance(self.result, str):
                return self.result[:200]
            elif isinstance(self.result, dict):
                return self.result.get("summary", str(self.result)[:200])
            return f"{self.tool} completed"
        elif self.status == ToolStatus.FAILED:
            return f"{self.tool} encountered an error"
        elif self.status == ToolStatus.CANCELLED:
            return f"{self.tool} was cancelled"
        elif self.status == ToolStatus.TIMED_OUT:
            return f"{self.tool} timed out"
        return f"{self.tool} is {self.status.value}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "tool": self.tool,
            "result": self.result,
            "error": self.error,
            "progress_pct": self.progress_pct,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ToolCall:
    """A tool invocation request."""

    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    timeout_ms: int = 10_000
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolExecutor:
    """
    Executes tool calls with streaming progress and cancellation.

    Usage:
        executor = ToolExecutor()
        async for progress in executor.execute_streaming(tool_call, token):
            if progress.status == ToolStatus.COMPLETED:
                # use progress.result
    """

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        """
        Args:
            tool_registry: Optional dict mapping tool names to callables.
                           If None, tools are resolved at runtime from MAS.
        """
        self._registry: Dict[str, Any] = tool_registry or {}

    def register(self, name: str, fn: Any) -> None:
        """Register a tool callable."""
        self._registry[name] = fn

    async def execute_streaming(
        self,
        tool_call: ToolCall,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[ToolProgress, None]:
        """
        Execute a tool with streaming progress updates.

        Yields:
            ToolProgress events: starting → [running…] → completed/failed/cancelled

        Args:
            tool_call: The tool to execute
            cancellation_token: Optional token; checked before and during execution
        """
        token = cancellation_token or CancellationToken()

        yield ToolProgress(
            status=ToolStatus.STARTING,
            tool=tool_call.name,
            message=f"Starting {tool_call.name}",
            progress_pct=0.0,
        )

        # Check for pre-cancellation
        if token.is_cancelled:
            yield ToolProgress(status=ToolStatus.CANCELLED, tool=tool_call.name)
            return

        try:
            result = await asyncio.wait_for(
                self._execute_with_cancellation(tool_call, token),
                timeout=tool_call.timeout_ms / 1000,
            )

            if token.is_cancelled:
                yield ToolProgress(status=ToolStatus.CANCELLED, tool=tool_call.name)
                return

            yield ToolProgress(
                status=ToolStatus.COMPLETED,
                tool=tool_call.name,
                result=result,
                progress_pct=1.0,
                message=f"{tool_call.name} completed",
            )

        except asyncio.TimeoutError:
            logger.warning(f"Tool {tool_call.name} timed out after {tool_call.timeout_ms}ms")
            yield ToolProgress(
                status=ToolStatus.TIMED_OUT,
                tool=tool_call.name,
                error=f"Timed out after {tool_call.timeout_ms}ms",
            )

        except asyncio.CancelledError:
            yield ToolProgress(status=ToolStatus.CANCELLED, tool=tool_call.name)

        except Exception as exc:
            logger.warning(f"Tool {tool_call.name} failed: {exc}")
            yield ToolProgress(
                status=ToolStatus.FAILED,
                tool=tool_call.name,
                error=str(exc),
            )

    async def _execute_with_cancellation(
        self,
        tool_call: ToolCall,
        token: CancellationToken,
    ) -> Any:
        """
        Execute the actual tool with periodic cancellation checks.
        """
        fn = self._registry.get(tool_call.name)

        if fn is not None:
            # Direct callable — call it
            if asyncio.iscoroutinefunction(fn):
                return await fn(**tool_call.args)
            else:
                return fn(**tool_call.args)

        # Fallback: attempt to resolve from MAS tool registry
        return await self._call_mas_tool(tool_call, token)

    async def _call_mas_tool(
        self,
        tool_call: ToolCall,
        token: CancellationToken,
    ) -> Any:
        """
        Resolve and call a tool through the MAS agent tool registry.
        Periodic cancellation checks every 200ms.
        """
        try:
            from mycosoft_mas.agents.base_agent import BaseAgent  # type: ignore

            # Build tool execution context
            context = {
                "tool": tool_call.name,
                "args": tool_call.args,
                **tool_call.metadata,
            }

            # Poll for result with cancellation checks
            result_future: asyncio.Future = asyncio.get_event_loop().create_future()

            async def _run():
                # Simple HTTP call to MAS tool endpoint if available
                import os
                import aiohttp  # type: ignore

                mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
                url = f"{mas_url}/api/tools/execute"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=context, timeout=aiohttp.ClientTimeout(total=tool_call.timeout_ms / 1000)) as resp:
                        data = await resp.json()
                        return data.get("result", data)

            task = asyncio.create_task(_run())
            while not task.done():
                if token.is_cancelled:
                    task.cancel()
                    raise asyncio.CancelledError()
                await asyncio.sleep(0.2)
            return await task

        except ImportError:
            raise RuntimeError(f"Tool {tool_call.name!r} not found in registry")

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall],
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[ToolProgress, None]:
        """
        Execute multiple tools in parallel, yielding progress as they complete.

        Yields updates from all tools interleaved by completion order.
        """
        token = cancellation_token or CancellationToken()

        async def _run_one(tc: ToolCall) -> AsyncGenerator[ToolProgress, None]:
            async for p in self.execute_streaming(tc, token):
                yield p

        tasks = [
            asyncio.create_task(self._collect(self.execute_streaming(tc, token)))
            for tc in tool_calls
        ]

        # Yield completion events as tasks finish
        for coro in asyncio.as_completed(tasks):
            progresses = await coro
            for p in progresses:
                yield p

    async def _collect(
        self,
        gen: AsyncGenerator[ToolProgress, None],
    ) -> List[ToolProgress]:
        """Drain an async generator into a list."""
        results = []
        async for p in gen:
            results.append(p)
        return results


async def speak_with_tools(
    response_gen: AsyncGenerator[str, None],
    tool_tasks: List[asyncio.Task],
    yield_status: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Yield speech tokens while tool tasks run in the background.

    Announces tool completions as they finish (interleaved with response).

    Args:
        response_gen: Token stream from LLM (may reference "I'm looking that up")
        tool_tasks: Concurrent asyncio Tasks running tool calls
        yield_status: If True, emit "I'm working on that…" preamble

    Yields:
        String tokens for TTS
    """
    if yield_status and tool_tasks:
        yield "I'm working on that for you — "

    # Yield the response tokens
    async for chunk in response_gen:
        yield chunk

    # Announce tool completions as they finish
    if tool_tasks:
        for coro in asyncio.as_completed(tool_tasks):
            try:
                result: Any = await coro
                if isinstance(result, ToolProgress) and result.status == ToolStatus.COMPLETED:
                    summary = result.summary
                    if summary:
                        yield f"\n\nUpdate: {summary}"
                elif isinstance(result, list):
                    for p in result:
                        if isinstance(p, ToolProgress) and p.status == ToolStatus.COMPLETED:
                            summary = p.summary
                            if summary:
                                yield f"\n\nUpdate: {summary}"
            except Exception as exc:
                logger.debug(f"speak_with_tools: tool task error: {exc}")


# Module-level singleton executor
_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get the global ToolExecutor instance."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
