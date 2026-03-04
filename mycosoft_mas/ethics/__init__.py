"""
MYCA Ethics Module - Three-Gate Pipeline

Truth Gate -> Incentive Gate -> Horizon Gate.
Developmental vessels, Clarity Brief, Stoic attention budgeting.
Created: March 3, 2026
"""

from mycosoft_mas.ethics.engine import EthicsEngine, EthicsResult, EthicsRiskLevel
from mycosoft_mas.ethics.truth_gate import TruthGate, TruthGateResult
from mycosoft_mas.ethics.incentive_gate import IncentiveGate, IncentiveGateResult
from mycosoft_mas.ethics.horizon_gate import HorizonGate, HorizonGateResult
from mycosoft_mas.ethics.clarity_brief import ClarityBrief, parse_clarity_brief
from mycosoft_mas.ethics.attention_budget import AttentionBudget
from mycosoft_mas.ethics.vessels import DevelopmentalVessel, get_vessel_prompt, get_gate_vessels
from mycosoft_mas.ethics.simulator import SecondOrderSimulator, SimulationResult, CausalNode

__all__ = [
    "EthicsEngine",
    "EthicsResult",
    "EthicsRiskLevel",
    "TruthGate",
    "TruthGateResult",
    "IncentiveGate",
    "IncentiveGateResult",
    "HorizonGate",
    "HorizonGateResult",
    "ClarityBrief",
    "parse_clarity_brief",
    "AttentionBudget",
    "DevelopmentalVessel",
    "get_vessel_prompt",
    "get_gate_vessels",
    "SecondOrderSimulator",
    "SimulationResult",
    "CausalNode",
]
