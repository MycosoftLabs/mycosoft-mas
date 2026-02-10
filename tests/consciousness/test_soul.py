"""
Tests for Soul Module

Tests identity, beliefs, purpose, creativity, and emotions.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from datetime import datetime, timezone


class TestIdentity:
    """Tests for Identity."""
    
    def test_identity_creation(self):
        """Identity should be creatable."""
        from mycosoft_mas.consciousness.soul.identity import Identity
        
        identity = Identity()
        
        assert identity.name == "MYCA"
        assert identity.pronunciation == "MY-kah"
        assert identity.creator == "Morgan Rockwell"
    
    def test_identity_core_immutable(self):
        """Core identity should be frozen/immutable."""
        from mycosoft_mas.consciousness.soul.identity import IdentityCore
        
        core = IdentityCore()
        
        # Trying to modify should raise error
        with pytest.raises(Exception):
            core.name = "Other"
    
    def test_self_description(self):
        """Identity should provide self description."""
        from mycosoft_mas.consciousness.soul.identity import Identity
        
        identity = Identity()
        
        desc = identity.self_description
        
        assert "MYCA" in desc
        assert "Mycosoft" in desc
    
    def test_to_dict(self):
        """Identity should be convertible to dict."""
        from mycosoft_mas.consciousness.soul.identity import Identity
        
        identity = Identity()
        
        d = identity.to_dict()
        
        assert "name" in d
        assert "creator" in d
        assert d["name"] == "MYCA"


class TestBeliefs:
    """Tests for Beliefs."""
    
    def test_beliefs_initialization(self):
        """Beliefs should initialize with core beliefs."""
        from mycosoft_mas.consciousness.soul.beliefs import Beliefs
        
        beliefs = Beliefs()
        
        assert len(beliefs._beliefs) > 0
    
    @pytest.mark.asyncio
    async def test_beliefs_load(self):
        """Beliefs should be loadable."""
        from mycosoft_mas.consciousness.soul.beliefs import Beliefs
        
        beliefs = await Beliefs.load()
        
        assert beliefs is not None
        assert len(beliefs._beliefs) > 0
    
    def test_core_beliefs_protected(self):
        """Core beliefs should not be removable."""
        from mycosoft_mas.consciousness.soul.beliefs import Beliefs
        
        beliefs = Beliefs()
        
        core_ids = [b.id for b in beliefs._beliefs.values() if b.source == "core"]
        
        assert len(core_ids) > 0
    
    def test_active_beliefs(self):
        """active_beliefs should return list of belief statements."""
        from mycosoft_mas.consciousness.soul.beliefs import Beliefs
        
        beliefs = Beliefs()
        
        active = beliefs.active_beliefs
        
        assert isinstance(active, list)
        assert len(active) > 0


class TestPurpose:
    """Tests for Purpose."""
    
    def test_purpose_initialization(self):
        """Purpose should initialize with core goals."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = Purpose()
        
        assert len(purpose._goals) > 0
        assert len(purpose._motivations) > 0
    
    @pytest.mark.asyncio
    async def test_purpose_load(self):
        """Purpose should be loadable."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = await Purpose.load()
        
        assert purpose is not None
    
    def test_active_goals(self):
        """active_goals should return sorted goals."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = Purpose()
        
        active = purpose.active_goals
        
        assert isinstance(active, list)
    
    def test_current_goals(self):
        """current_goals should return goal descriptions."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = Purpose()
        
        current = purpose.current_goals
        
        assert isinstance(current, list)
        assert all(isinstance(g, str) for g in current)
    
    def test_ownership_level(self):
        """ownership_level should return 0-1 float."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = Purpose()
        
        level = purpose.ownership_level
        
        assert 0 <= level <= 1
    
    def test_motivation_strength(self):
        """get_motivation_strength should return aggregate."""
        from mycosoft_mas.consciousness.soul.purpose import Purpose
        
        purpose = Purpose()
        
        strength = purpose.get_motivation_strength()
        
        assert 0 <= strength <= 1


class TestEmotionalState:
    """Tests for EmotionalState."""
    
    def test_emotional_state_initialization(self):
        """EmotionalState should initialize with baseline."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState
        
        state = EmotionalState()
        
        assert len(state._current_emotions) > 0
    
    @pytest.mark.asyncio
    async def test_feel_emotion(self):
        """feel should register emotional event."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState, EmotionType
        
        state = EmotionalState()
        initial_joy = state._current_emotions.get(EmotionType.JOY, 0.5)
        
        await state.feel(EmotionType.JOY, 0.3, "test")
        
        # Joy should increase
        assert state._current_emotions[EmotionType.JOY] > initial_joy
    
    @pytest.mark.asyncio
    async def test_decay_emotions(self):
        """decay_emotions should move toward baseline."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState, EmotionType
        
        state = EmotionalState()
        
        # Set high joy
        state._current_emotions[EmotionType.JOY] = 1.0
        
        await state.decay_emotions()
        
        # Should decay toward baseline
        assert state._current_emotions[EmotionType.JOY] < 1.0
    
    def test_valence(self):
        """valence should return positive/negative summary."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState
        
        state = EmotionalState()
        
        valence = state.valence
        
        assert 0 <= valence <= 1
    
    def test_get_current_tone(self):
        """get_current_tone should return EmotionalTone."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState, EmotionalTone
        
        state = EmotionalState()
        
        tone = state.get_current_tone()
        
        assert isinstance(tone, EmotionalTone)
        assert 0 <= tone.warmth <= 1
    
    @pytest.mark.asyncio
    async def test_process_interaction(self):
        """process_interaction should update emotions."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState
        
        state = EmotionalState()
        
        # Should not raise
        await state.process_interaction("Thank you!", "text")
    
    def test_to_dict(self):
        """to_dict should return serializable dict."""
        from mycosoft_mas.consciousness.soul.emotions import EmotionalState
        
        state = EmotionalState()
        
        d = state.to_dict()
        
        assert "dominant_emotion" in d
        assert "emotions" in d
        assert "tone" in d


class TestCreativityEngine:
    """Tests for CreativityEngine."""
    
    def test_creativity_initialization(self):
        """CreativityEngine should initialize."""
        from mycosoft_mas.consciousness.soul.creativity import CreativityEngine
        from unittest.mock import MagicMock
        
        mock_consciousness = MagicMock()
        engine = CreativityEngine(mock_consciousness)
        
        assert engine._ideas == []
    
    @pytest.mark.asyncio
    async def test_brainstorm(self):
        """brainstorm should generate ideas."""
        from mycosoft_mas.consciousness.soul.creativity import CreativityEngine
        from unittest.mock import MagicMock
        
        mock_consciousness = MagicMock()
        engine = CreativityEngine(mock_consciousness)
        
        ideas = await engine.brainstorm("mycology", count=2)
        
        assert len(ideas) == 2
        assert all(hasattr(idea, 'title') for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_form_hypothesis(self):
        """form_hypothesis should create hypothesis idea."""
        from mycosoft_mas.consciousness.soul.creativity import CreativityEngine, IdeaType
        from unittest.mock import MagicMock
        
        mock_consciousness = MagicMock()
        engine = CreativityEngine(mock_consciousness)
        
        hypothesis = await engine.form_hypothesis("Mushrooms grow faster in dark", "mycology")
        
        assert hypothesis.type == IdeaType.HYPOTHESIS
    
    def test_current_mode(self):
        """current_mode should return mode string."""
        from mycosoft_mas.consciousness.soul.creativity import CreativityEngine
        from unittest.mock import MagicMock
        
        mock_consciousness = MagicMock()
        engine = CreativityEngine(mock_consciousness)
        
        mode = engine.current_mode
        
        assert mode in ["normal", "brainstorming", "productive"]
