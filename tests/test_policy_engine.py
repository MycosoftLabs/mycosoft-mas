"""
Tests for Policy Engine - February 9, 2026

Unit tests for event validation, tool whitelist, rate limiting.
"""

import pytest

pytest.importorskip("jsonschema", reason="jsonschema required for security module")

from unittest.mock import patch

from mycosoft_mas.realtime.event_schema import AgentEvent
from mycosoft_mas.security.policy_engine import (
    PolicyEngine,
)


class TestPolicyEngine:
    """Tests for PolicyEngine."""

    @patch.dict("os.environ", {"MYCA_POLICY_ENGINE_ENABLED": "false"})
    def test_disabled_allows_all(self):
        """When disabled, all events pass."""
        engine = PolicyEngine(enabled=False)
        ev = AgentEvent(type="task", from_agent="a", to_agent="b")
        result = engine.validate_event(ev)
        assert result.allowed is True
        assert "disabled" in result.reason.lower()

    @patch.dict("os.environ", {"MYCA_POLICY_ENGINE_ENABLED": "true"})
    def test_invalid_classification_blocked(self):
        """Invalid classification is blocked."""
        engine = PolicyEngine(enabled=True)
        ev = AgentEvent(
            type="task",
            from_agent="a",
            to_agent="b",
            classification="SECRET",
        )
        result = engine.validate_event(ev)
        assert result.allowed is False
        assert "classification" in result.reason.lower()

    @patch.dict("os.environ", {"MYCA_POLICY_ENGINE_ENABLED": "true"})
    def test_valid_unclass_passes(self):
        """Valid UNCLASS event passes when tool_call has no tool."""
        engine = PolicyEngine(enabled=True)
        ev = AgentEvent(
            type="heartbeat",
            from_agent="a",
            to_agent="b",
            payload={},
        )
        result = engine.validate_event(ev)
        assert result.allowed is True
