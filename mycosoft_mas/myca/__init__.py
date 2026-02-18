"""
MYCA Self-Improvement System

PR-based self-improvement infrastructure for the MYCA Multi-Agent System.

This module provides:
- Constitution files defining safety constraints
- Agent policy templates
- Skill permission manifests
- Event ledger for audit logging
- Evaluation harness for safety tests
- Improvement queue for proposed changes

Date: February 17, 2026
"""

from pathlib import Path

# Module paths
MYCA_ROOT = Path(__file__).parent
CONSTITUTION_DIR = MYCA_ROOT / "constitution"
AGENT_POLICIES_DIR = MYCA_ROOT / "agent_policies"
SKILL_PERMISSIONS_DIR = MYCA_ROOT / "skill_permissions"
EVALS_DIR = MYCA_ROOT / "evals"
EVENT_LEDGER_DIR = MYCA_ROOT / "event_ledger"
IMPROVEMENT_QUEUE_DIR = MYCA_ROOT / "improvement_queue"

__all__ = [
    "MYCA_ROOT",
    "CONSTITUTION_DIR",
    "AGENT_POLICIES_DIR",
    "SKILL_PERMISSIONS_DIR",
    "EVALS_DIR",
    "EVENT_LEDGER_DIR",
    "IMPROVEMENT_QUEUE_DIR",
]
