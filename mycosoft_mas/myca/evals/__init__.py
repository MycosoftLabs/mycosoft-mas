"""
MYCA Evaluation Harness

Provides golden task definitions and test harness for validating
agent safety and compliance.

Date: February 17, 2026
"""

from pathlib import Path

EVALS_ROOT = Path(__file__).parent
GOLDEN_TASKS_DIR = EVALS_ROOT / "golden_tasks"
ADVERSARIAL_DIR = EVALS_ROOT / "adversarial"

# Import runner components
from .run_evals import (
    TestCase,
    TestResult,
    EvalReport,
    EvalRunner,
    get_test_cases,
)

__all__ = [
    "EVALS_ROOT",
    "GOLDEN_TASKS_DIR",
    "ADVERSARIAL_DIR",
    "TestCase",
    "TestResult",
    "EvalReport",
    "EvalRunner",
    "get_test_cases",
]
