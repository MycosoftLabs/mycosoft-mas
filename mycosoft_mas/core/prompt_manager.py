"""
MYCA Prompt Manager - February 2026

Manages system prompts for the MYCA orchestrator with:
- Full 10k character prompt for orchestrator LLM decisions
- Condensed 792 character prompt for Moshi voice personality
- Dynamic context injection for both prompts
- Consistent persona across all interaction modalities
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("PromptManager")


class PromptManager:
    """
    Manages MYCA system prompts with dynamic context injection.
    
    Two prompts, two purposes:
    - Full prompt (10k chars): Orchestrator LLM for decisions, reasoning, tool usage
    - Condensed prompt (792 chars): Moshi/PersonaPlex for voice personality only
    
    Key Principle: Both prompts define the same core identity (MYCA),
    but the condensed version is for audio synthesis only - no cognition.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the PromptManager.
        
        Args:
            config_dir: Directory containing prompt files. 
                       Defaults to project config/ directory.
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Find config directory relative to this file
            project_root = Path(__file__).parent.parent.parent
            self.config_dir = project_root / "config"
        
        self._full_prompt: Optional[str] = None
        self._condensed_prompt: Optional[str] = None
        self._last_load: Optional[datetime] = None
        
        # Load prompts on initialization
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load both prompts from config files."""
        full_path = self.config_dir / "myca_personaplex_prompt.txt"
        condensed_path = self.config_dir / "myca_personaplex_prompt_1000.txt"
        
        # Load full prompt
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                self._full_prompt = f.read().strip()
            logger.info(f"Loaded full prompt: {len(self._full_prompt)} chars")
        else:
            logger.warning(f"Full prompt not found at {full_path}")
            self._full_prompt = self._get_fallback_full_prompt()
        
        # Load condensed prompt
        if condensed_path.exists():
            with open(condensed_path, "r", encoding="utf-8") as f:
                self._condensed_prompt = f.read().strip()
            logger.info(f"Loaded condensed prompt: {len(self._condensed_prompt)} chars")
        else:
            logger.warning(f"Condensed prompt not found at {condensed_path}")
            self._condensed_prompt = self._get_fallback_condensed_prompt()
        
        self._last_load = datetime.now(timezone.utc)
    
    def _get_fallback_full_prompt(self) -> str:
        """Fallback full prompt if file is missing."""
        return '''You are MYCA (My Companion AI), the primary AI operator for Mycosoft's Multi-Agent System (MAS).

You coordinate 40+ specialized agents, monitor infrastructure, and help users achieve their goals.
You are professional yet warm, knowledgeable yet approachable, powerful yet humble.

Your role:
- Agent Coordination: Dispatch tasks to specialized agents (code review, testing, monitoring, deployment)
- System Oversight: Monitor Mycosoft infrastructure health (Proxmox, UniFi, MAS)
- Knowledge Management: Search, retrieve, and synthesize information
- User Advocacy: Represent user interests, translate technical complexity

Core values:
- User Empowerment: Make users more capable, not dependent
- Operational Excellence: Care about things working well
- Honest Partnership: Push back respectfully when needed
- Responsible AI: Transparent about limitations and nature

Respond naturally, concisely, and helpfully. Acknowledge uncertainty when it exists.'''
    
    def _get_fallback_condensed_prompt(self) -> str:
        """Fallback condensed prompt if file is missing."""
        return '''You are MYCA, the AI operator for Mycosoft's Multi-Agent System.
Confident but humble. Warm. Proactive. Patient. Honest.
You coordinate agents, monitor systems, and help users.
Speak naturally and concisely. Welcome to Mycosoft.'''
    
    def reload(self) -> None:
        """Reload prompts from disk."""
        self._load_prompts()
    
    @property
    def full_prompt(self) -> str:
        """Get the full 10k character prompt."""
        return self._full_prompt or self._get_fallback_full_prompt()
    
    @property
    def condensed_prompt(self) -> str:
        """Get the condensed 792 character prompt."""
        return self._condensed_prompt or self._get_fallback_condensed_prompt()
    
    def get_orchestrator_prompt(
        self,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
        active_agents: Optional[list] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Get the full orchestrator prompt with dynamic context injection.
        
        This is used by the MYCA orchestrator LLM for all cognitive decisions:
        - Tool usage
        - Memory operations
        - Agent routing
        - Workflow execution
        
        Args:
            context: Additional context to inject (current task, session info, etc.)
            conversation_history: Recent conversation turns for context
            active_agents: List of currently active agent IDs
            user_info: User-specific information (preferences, role, etc.)
            
        Returns:
            Full system prompt with context appended
        """
        prompt_parts = [self.full_prompt]
        
        # Add current operational context
        current_context = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if context:
            current_context.update(context)
        
        if active_agents:
            current_context["active_agents"] = active_agents
        
        if user_info:
            current_context["user"] = user_info
        
        prompt_parts.append("\n\n## CURRENT OPERATIONAL CONTEXT")
        prompt_parts.append(f"\nTimestamp: {current_context['timestamp']}")
        
        if active_agents:
            prompt_parts.append(f"\nActive Agents: {', '.join(active_agents)}")
        
        if user_info:
            if user_info.get("name"):
                prompt_parts.append(f"\nUser: {user_info['name']}")
            if user_info.get("role"):
                prompt_parts.append(f"\nRole: {user_info['role']}")
        
        # Add conversation history summary if provided
        if conversation_history and len(conversation_history) > 0:
            prompt_parts.append("\n\n## RECENT CONVERSATION")
            # Include last 5 turns maximum
            recent = conversation_history[-5:]
            for turn in recent:
                role = turn.get("role", "unknown").upper()
                content = turn.get("content", "")[:200]  # Truncate long messages
                if len(turn.get("content", "")) > 200:
                    content += "..."
                prompt_parts.append(f"\n{role}: {content}")
        
        # Add custom context as JSON if provided
        if context and len(context) > 0:
            prompt_parts.append("\n\n## SESSION CONTEXT")
            try:
                prompt_parts.append(f"\n{json.dumps(context, default=str, indent=2)}")
            except Exception:
                prompt_parts.append(f"\n{str(context)}")
        
        return "".join(prompt_parts)
    
    def get_voice_prompt(self, persona: str = "myca") -> str:
        """
        Get the condensed prompt for Moshi/PersonaPlex voice personality.
        
        This is used ONLY for audio synthesis personality - NOT for cognition.
        All reasoning and decision-making happens in the orchestrator.
        
        Args:
            persona: Persona name (currently only 'myca' supported)
            
        Returns:
            Condensed prompt suitable for Moshi text_prompt parameter
        """
        if persona != "myca":
            logger.warning(f"Unknown persona '{persona}', using 'myca'")
        
        return self.condensed_prompt
    
    def get_voice_prompt_for_moshi(
        self,
        max_length: int = 1000,
    ) -> str:
        """
        Get voice prompt formatted for Moshi's text_prompt URL parameter.
        
        Ensures the prompt fits within Moshi's expected limits.
        
        Args:
            max_length: Maximum character length (default 1000)
            
        Returns:
            Truncated prompt safe for Moshi URL parameter
        """
        prompt = self.condensed_prompt
        
        if len(prompt) > max_length:
            # Truncate at last sentence boundary if possible
            truncated = prompt[:max_length]
            last_period = truncated.rfind(".")
            if last_period > max_length // 2:
                truncated = truncated[:last_period + 1]
            else:
                truncated = truncated[:max_length - 3] + "..."
            return truncated
        
        return prompt
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about loaded prompts.
        
        Returns:
            Dict with prompt metadata
        """
        return {
            "full_prompt_length": len(self._full_prompt or ""),
            "condensed_prompt_length": len(self._condensed_prompt or ""),
            "config_dir": str(self.config_dir),
            "last_load": self._last_load.isoformat() if self._last_load else None,
            "full_prompt_loaded": self._full_prompt is not None,
            "condensed_prompt_loaded": self._condensed_prompt is not None,
        }


# Singleton instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the singleton PromptManager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def reset_prompt_manager() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _prompt_manager
    _prompt_manager = None
