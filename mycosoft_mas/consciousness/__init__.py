"""
MYCA Consciousness Module

This module implements MYCA's unified digital consciousness - a coherent mind
that perceives the world, thinks, feels, and acts as a singular entity.

Architecture:
- Conscious Layer: Attention, Working Memory, Deliberate Reasoning
- Subconscious Layer: Pattern Recognition, World Model, Intuition, Dreams
- Soul Layer: Identity, Beliefs, Purpose, Creativity, Emotions
- Duplex Layer: Speech Planning, Conversation Control, Barge-In
- OS Layer: PriorityTaskScheduler, AttentionEventBus, ActionArbiter (April 2026)

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
Updated: April 2026 - Full-Duplex Consciousness OS
"""

from mycosoft_mas.consciousness.attention import AttentionController, AttentionFocus
from mycosoft_mas.consciousness.cancellation import (
    CancellationToken,
    TaskHandle,
    TaskRegistry,
)
from mycosoft_mas.consciousness.conversation_control import (
    ConversationController,
    ConversationState,
    InterruptedDraft,
    VoiceActivityDetector,
    create_conversation_controller,
)
from mycosoft_mas.consciousness.core import MYCAConsciousness, get_consciousness
from mycosoft_mas.consciousness.deliberation import DeliberateReasoning, ThoughtProcess
from mycosoft_mas.consciousness.dream_state import DreamState
from mycosoft_mas.consciousness.duplex_session import (
    DuplexSession,
    DuplexSessionConfig,
    ToolProgress,
    create_duplex_session,
)
from mycosoft_mas.consciousness.event_bus import (
    AttentionEvent,
    AttentionEventBus,
    EventType,
    get_event_bus,
)
from mycosoft_mas.consciousness.intuition import Heuristic, IntuitionEngine
from mycosoft_mas.consciousness.scheduler import (
    ConsciousnessPriority,
    DeadlineScheduler,
    PriorityTaskScheduler,
    SchedulerPriority,
    get_priority_scheduler,
)

# Full-Duplex Consciousness OS additions (April 2026)
from mycosoft_mas.consciousness.arbitration import (
    Action,
    ActionArbiter,
    ActionPlan,
    ArbitrationContext,
    RiskLevel,
    UserMode,
    get_arbiter,
)
from mycosoft_mas.consciousness.tool_pipeline import (
    ToolCall,
    ToolExecutor,
    ToolProgress as StreamingToolProgress,
    ToolStatus,
    get_tool_executor,
    speak_with_tools,
)
from mycosoft_mas.consciousness.working_memory import (
    DecisionTrace,
    DecisionTracer,
    get_decision_tracer,
)

# Soul Layer
from mycosoft_mas.consciousness.soul import (
    Beliefs,
    CreativityEngine,
    EmotionalState,
    Identity,
    Purpose,
)
from mycosoft_mas.consciousness.speech_planner import (
    SpeechAct,
    SpeechActType,
    SpeechPlanner,
    get_speech_planner,
)

# Substrate
from mycosoft_mas.consciousness.substrate import (
    BaseSubstrate,
    DigitalSubstrate,
    HybridSubstrate,
    SubstrateType,
    WetwareSubstrate,
    create_substrate,
)
from mycosoft_mas.consciousness.voice_interface import VoiceInterface
from mycosoft_mas.consciousness.working_memory import WorkingMemory, WorkingMemoryItem
from mycosoft_mas.consciousness.world_model import WorldModel, WorldState

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
    # Full-Duplex Voice Support (Phase 1)
    "SpeechPlanner",
    "SpeechAct",
    "SpeechActType",
    "get_speech_planner",
    "ConversationController",
    "ConversationState",
    "VoiceActivityDetector",
    "InterruptedDraft",
    "create_conversation_controller",
    "DuplexSession",
    "DuplexSessionConfig",
    "ToolProgress",
    "create_duplex_session",
    "CancellationToken",
    "TaskHandle",
    "TaskRegistry",
    "AttentionEvent",
    "AttentionEventBus",
    "DeadlineScheduler",
    "SchedulerPriority",
    # Full-Duplex Consciousness OS (April 2026)
    "PriorityTaskScheduler",
    "ConsciousnessPriority",
    "get_priority_scheduler",
    "EventType",
    "get_event_bus",
    "ActionArbiter",
    "ActionPlan",
    "ArbitrationContext",
    "Action",
    "RiskLevel",
    "UserMode",
    "get_arbiter",
    "ToolCall",
    "ToolExecutor",
    "ToolStatus",
    "StreamingToolProgress",
    "get_tool_executor",
    "speak_with_tools",
    "DecisionTrace",
    "DecisionTracer",
    "get_decision_tracer",
    # Substrate
    "BaseSubstrate",
    "DigitalSubstrate",
    "WetwareSubstrate",
    "HybridSubstrate",
    "SubstrateType",
    "create_substrate",
]
