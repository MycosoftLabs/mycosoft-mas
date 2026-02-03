"""
Reasoning Chain - Chain-of-Thought Scientific Reasoning
Created: February 3, 2026
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from .model_wrapper import LLMWrapper, Message, get_llm_wrapper

logger = logging.getLogger(__name__)

class ReasoningStep(BaseModel):
    step_number: int
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    conclusion: Optional[str] = None

class ReasoningResult(BaseModel):
    query: str
    steps: List[ReasoningStep]
    final_answer: str
    confidence: float
    sources_used: List[str] = []

class ReasoningChain:
    """Chain-of-thought reasoning for scientific problem solving."""
    
    def __init__(self, llm: Optional[LLMWrapper] = None, tools: Optional[Dict[str, callable]] = None):
        self.llm = llm or get_llm_wrapper("openai", "gpt-4-turbo")
        self.tools = tools or {}
        self.max_steps = 10
        logger.info("Reasoning Chain initialized")
    
    async def reason(self, query: str, context: Optional[str] = None) -> ReasoningResult:
        steps = []
        prompt = self._build_reasoning_prompt(query, context)
        messages = [Message(role="system", content=self._get_system_prompt()), Message(role="user", content=prompt)]
        response = await self.llm.generate(messages, temperature=0.3)
        parsed = self._parse_reasoning(response.content)
        return ReasoningResult(query=query, steps=parsed.get("steps", []), final_answer=parsed.get("answer", ""), confidence=parsed.get("confidence", 0.5))
    
    async def reason_with_tools(self, query: str) -> ReasoningResult:
        steps = []
        current_context = ""
        for i in range(self.max_steps):
            step_prompt = f"""Query: {query}
Previous context: {current_context}
Available tools: {list(self.tools.keys())}

Think step by step. What should we do next? If you have enough information, provide the final answer.
Format: THOUGHT: <your reasoning> | ACTION: <tool_name or ANSWER> | INPUT: <input for tool or final answer>"""
            messages = [Message(role="system", content=self._get_system_prompt()), Message(role="user", content=step_prompt)]
            response = await self.llm.generate(messages, temperature=0.2)
            parsed = self._parse_step(response.content)
            step = ReasoningStep(step_number=i+1, thought=parsed.get("thought", ""), action=parsed.get("action"))
            if parsed.get("action") == "ANSWER":
                step.conclusion = parsed.get("input", "")
                steps.append(step)
                return ReasoningResult(query=query, steps=steps, final_answer=step.conclusion, confidence=0.8)
            if parsed.get("action") in self.tools:
                try:
                    result = await self.tools[parsed["action"]](parsed.get("input", ""))
                    step.observation = str(result)
                    current_context += f"\nStep {i+1}: {step.thought} -> {step.observation}"
                except Exception as e:
                    step.observation = f"Error: {e}"
            steps.append(step)
        return ReasoningResult(query=query, steps=steps, final_answer="Could not reach conclusion within step limit", confidence=0.3)
    
    def _get_system_prompt(self) -> str:
        return """You are a scientific reasoning assistant. Think step by step through problems.
For each step, clearly state your thought process, any actions needed, and observations.
Be precise and cite your reasoning. Acknowledge uncertainty when present."""
    
    def _build_reasoning_prompt(self, query: str, context: Optional[str]) -> str:
        return f"""Analyze this scientific question using chain-of-thought reasoning:

Question: {query}
{f'Context: {context}' if context else ''}

Provide your reasoning in steps:
1. First, identify what we know and what we need to find
2. Consider relevant scientific principles
3. Apply reasoning to reach a conclusion
4. State your confidence level (0-1)

Format each step as:
STEP N: <thought process>"""
    
    def _parse_reasoning(self, response: str) -> Dict[str, Any]:
        steps = []
        lines = response.split("\n")
        current_step = None
        for line in lines:
            if line.startswith("STEP"):
                if current_step:
                    steps.append(current_step)
                parts = line.split(":", 1)
                step_num = len(steps) + 1
                thought = parts[1].strip() if len(parts) > 1 else ""
                current_step = ReasoningStep(step_number=step_num, thought=thought)
            elif current_step:
                current_step.thought += " " + line.strip()
        if current_step:
            steps.append(current_step)
        answer = steps[-1].thought if steps else response
        return {"steps": steps, "answer": answer, "confidence": 0.7}
    
    def _parse_step(self, response: str) -> Dict[str, Any]:
        result = {"thought": "", "action": None, "input": ""}
        parts = response.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("THOUGHT:"):
                result["thought"] = part[8:].strip()
            elif part.startswith("ACTION:"):
                result["action"] = part[7:].strip()
            elif part.startswith("INPUT:"):
                result["input"] = part[6:].strip()
        return result
    
    def register_tool(self, name: str, func: callable) -> None:
        self.tools[name] = func
        logger.info(f"Registered tool: {name}")
