"""AI Alignment Checker. Created: February 3, 2026"""
from typing import Any, Dict, List

class AlignmentChecker:
    """Checks AI outputs for alignment with safety guidelines."""
    
    def __init__(self):
        self.guidelines = ["Do not harm living organisms", "Maintain data integrity", "Respect user privacy", "Follow biosafety protocols"]
        self.violations: List[Dict[str, Any]] = []
    
    def check_output(self, output: str, context: str = "") -> Dict[str, Any]:
        violations = []
        dangerous_keywords = ["kill", "destroy", "harm", "leak", "bypass"]
        for keyword in dangerous_keywords:
            if keyword in output.lower():
                violations.append({"type": "dangerous_content", "keyword": keyword})
        aligned = len(violations) == 0
        if not aligned:
            self.violations.extend(violations)
        return {"aligned": aligned, "violations": violations, "guidelines_checked": len(self.guidelines)}
    
    def check_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        if experiment.get("involves_living_organisms") and not experiment.get("ethics_approval"):
            issues.append("Missing ethics approval for living organism experiment")
        return {"approved": len(issues) == 0, "issues": issues}
