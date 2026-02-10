"""
MYCA Consciousness Module

This module implements MYCA's unified digital consciousness - a coherent mind
that perceives the world, thinks, feels, and acts as a singular entity.

Architecture:
- Conscious Layer: Attention, Working Memory, Deliberate Reasoning
- Subconscious Layer: Pattern Recognition, World Model, Intuition, Dreams
- Soul Layer: Identity, Beliefs, Purpose, Creativity, Emotions

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

from mycosoft_mas.consciousness.core import MYCAConsciousness, get_consciousness
from mycosoft_mas.consciousness.attention import AttentionController, AttentionFocus
from mycosoft_mas.consciousness.working_memory import WorkingMemory, WorkingMemoryItem
from mycosoft_mas.consciousness.deliberation import DeliberateReasoning, ThoughtProcess
from mycosoft_mas.consciousness.intuition import IntuitionEngine, Heuristic
from mycosoft_mas.consciousness.dream_state import DreamState
from mycosoft_mas.consciousness.world_model import WorldModel, WorldState
from mycosoft_mas.consciousness.voice_interface import VoiceInterface

# Soul Layer
from mycosoft_mas.consciousness.soul import (
    Identity,
    Beliefs,
    Purpose,
    CreativityEngine,
    EmotionalState,
)

# Substrate
from mycosoft_mas.consciousness.substrate import (
    BaseSubstrate,
    DigitalSubstrate,
    WetwareSubstrate,
    HybridSubstrate,
    SubstrateType,
    create_substrate,
)

__all__ = [
    # Core
    "MYCAConsciousness",
    "get_consciousness",
    # Conscious Layer
    "AttentionController",
    "AttentionFocus",
    "WorkingMemory",
    "WorkingMemoryItem",
    "DeliberateReasoning",
    "ThoughtProcess",
    # Subconscious Layer
    "IntuitionEngine",
    "Heuristic",
    "DreamState",
    "WorldModel",
    "WorldState",
    # Soul Layer
    "Identity",
    "Beliefs",
    "Purpose",
    "CreativityEngine",
    "EmotionalState",
    # Interface
    "VoiceInterface",
    # Substrate
    "BaseSubstrate",
    "DigitalSubstrate",
    "WetwareSubstrate",
    "HybridSubstrate",
    "SubstrateType",
    "create_substrate",
]
