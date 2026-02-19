"""
Learning Feedback Service for Auto-Learning System.
Created: February 12, 2026

Tracks task outcomes and learns from them:
- Track task outcomes (success/failure)
- Correlate fixes with results
- Learn which approaches work best
- Adjust agent behavior based on metrics
- Store learned patterns in memory

Used by the autonomous operator for continuous improvement.
"""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LearningFeedback")


@dataclass
class TaskOutcome:
    """Record of a task outcome."""
    outcome_id: str
    task_type: str
    agent_id: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    retry_count: int = 0
    approach_used: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearnedPattern:
    """A pattern learned from task outcomes."""
    pattern_id: str
    task_type: str
    successful_approach: str
    success_rate: float
    sample_size: int
    conditions: Dict[str, Any] = field(default_factory=dict)
    learned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentPerformance:
    """Performance metrics for an agent."""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_duration: float = 0.0
    success_rate: float = 0.0
    common_errors: Dict[str, int] = field(default_factory=dict)
    best_task_types: List[str] = field(default_factory=list)


class LearningFeedbackService:
    """
    Service for tracking outcomes and learning from them.
    
    Features:
    - Outcome tracking with persistence
    - Agent performance metrics
    - Pattern recognition from successes/failures
    - Approach recommendation based on history
    - Error correlation and prevention
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = Path(data_dir or os.path.join(
            os.path.dirname(__file__), "../../data/learning"
        ))
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Data stores
        self._outcomes: List[TaskOutcome] = []
        self._patterns: Dict[str, LearnedPattern] = {}
        self._agent_stats: Dict[str, AgentPerformance] = defaultdict(lambda: AgentPerformance(agent_id=""))
        
        # Approach success tracking
        self._approach_outcomes: Dict[str, Dict[str, List[bool]]] = defaultdict(lambda: defaultdict(list))
        
        # Error patterns
        self._error_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Load persisted data."""
        outcomes_file = self._data_dir / "outcomes.json"
        if outcomes_file.exists():
            try:
                with open(outcomes_file, "r") as f:
                    data = json.load(f)
                    self._outcomes = [TaskOutcome(**o) for o in data]
                    self._rebuild_statistics()
            except Exception as e:
                logger.error(f"Failed to load outcomes: {e}")
        
        patterns_file = self._data_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, "r") as f:
                    data = json.load(f)
                    self._patterns = {k: LearnedPattern(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")
    
    def _save_data(self) -> None:
        """Persist data to disk."""
        # Save outcomes (keep last 1000)
        outcomes_file = self._data_dir / "outcomes.json"
        recent_outcomes = self._outcomes[-1000:]
        with open(outcomes_file, "w") as f:
            json.dump([
                {
                    "outcome_id": o.outcome_id, "task_type": o.task_type,
                    "agent_id": o.agent_id, "success": o.success,
                    "duration_seconds": o.duration_seconds,
                    "error_message": o.error_message, "retry_count": o.retry_count,
                    "approach_used": o.approach_used, "timestamp": o.timestamp,
                    "metadata": o.metadata
                }
                for o in recent_outcomes
            ], f, indent=2)
        
        # Save patterns
        patterns_file = self._data_dir / "patterns.json"
        with open(patterns_file, "w") as f:
            json.dump({
                k: {
                    "pattern_id": p.pattern_id, "task_type": p.task_type,
                    "successful_approach": p.successful_approach,
                    "success_rate": p.success_rate, "sample_size": p.sample_size,
                    "conditions": p.conditions, "learned_at": p.learned_at
                }
                for k, p in self._patterns.items()
            }, f, indent=2)
    
    def _rebuild_statistics(self) -> None:
        """Rebuild statistics from outcomes."""
        self._agent_stats.clear()
        self._approach_outcomes.clear()
        self._error_patterns.clear()
        
        for outcome in self._outcomes:
            self._update_statistics(outcome)
    
    def _update_statistics(self, outcome: TaskOutcome) -> None:
        """Update statistics with a new outcome."""
        # Agent stats
        agent_id = outcome.agent_id
        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = AgentPerformance(agent_id=agent_id)
        
        stats = self._agent_stats[agent_id]
        stats.total_tasks += 1
        if outcome.success:
            stats.successful_tasks += 1
        else:
            stats.failed_tasks += 1
            if outcome.error_message:
                error_key = outcome.error_message[:100]
                stats.common_errors[error_key] = stats.common_errors.get(error_key, 0) + 1
        
        stats.success_rate = stats.successful_tasks / stats.total_tasks if stats.total_tasks > 0 else 0
        
        # Update average duration
        old_avg = stats.avg_duration
        stats.avg_duration = old_avg + (outcome.duration_seconds - old_avg) / stats.total_tasks
        
        # Approach tracking
        if outcome.approach_used:
            self._approach_outcomes[outcome.task_type][outcome.approach_used].append(outcome.success)
        
        # Error pattern tracking
        if not outcome.success and outcome.error_message:
            self._error_patterns[outcome.task_type].append({
                "error": outcome.error_message,
                "approach": outcome.approach_used,
                "agent_id": outcome.agent_id,
                "timestamp": outcome.timestamp
            })
    
    def record_outcome(
        self,
        task_type: str,
        agent_id: str,
        success: bool,
        duration_seconds: float,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        approach_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a task outcome."""
        outcome = TaskOutcome(
            outcome_id=str(uuid4())[:8],
            task_type=task_type,
            agent_id=agent_id,
            success=success,
            duration_seconds=duration_seconds,
            error_message=error_message,
            retry_count=retry_count,
            approach_used=approach_used,
            metadata=metadata or {}
        )
        
        self._outcomes.append(outcome)
        self._update_statistics(outcome)
        
        # Check for new patterns
        self._detect_patterns(task_type)
        
        # Save periodically
        if len(self._outcomes) % 10 == 0:
            self._save_data()
        
        logger.info(f"Recorded outcome: {outcome.outcome_id} ({task_type}, success={success})")
        return outcome.outcome_id
    
    def _detect_patterns(self, task_type: str) -> None:
        """Detect patterns from outcomes for a task type."""
        approaches = self._approach_outcomes.get(task_type, {})
        
        for approach, results in approaches.items():
            if len(results) >= 5:  # Minimum sample size
                success_rate = sum(results) / len(results)
                
                if success_rate >= 0.8:  # High success rate threshold
                    pattern_id = f"{task_type}_{approach}"
                    
                    self._patterns[pattern_id] = LearnedPattern(
                        pattern_id=pattern_id,
                        task_type=task_type,
                        successful_approach=approach,
                        success_rate=success_rate,
                        sample_size=len(results)
                    )
                    
                    logger.info(f"Learned pattern: {approach} works well for {task_type} ({success_rate:.0%} success)")
    
    def get_recommended_approach(self, task_type: str) -> Optional[str]:
        """Get recommended approach for a task type based on learned patterns."""
        best_approach = None
        best_rate = 0.0
        
        for pattern in self._patterns.values():
            if pattern.task_type == task_type and pattern.success_rate > best_rate:
                best_rate = pattern.success_rate
                best_approach = pattern.successful_approach
        
        return best_approach
    
    def get_agent_performance(self, agent_id: str) -> Optional[AgentPerformance]:
        """Get performance metrics for an agent."""
        return self._agent_stats.get(agent_id)

    def record_workflow_execution(
        self,
        workflow_name: str,
        success: bool,
        duration_seconds: float,
        error_message: Optional[str] = None,
    ) -> str:
        """Record a workflow execution outcome for learning and performance tracking."""
        return self.record_outcome(
            task_type="workflow_execution",
            agent_id="n8n",
            success=success,
            duration_seconds=duration_seconds,
            error_message=error_message,
            metadata={"workflow_name": workflow_name},
        )

    def get_workflow_performance(self) -> List[Dict[str, Any]]:
        """Aggregate execution stats per workflow (success/failure rates, avg duration)."""
        by_workflow: Dict[str, Dict[str, Any]] = {}
        for o in self._outcomes:
            if o.task_type != "workflow_execution":
                continue
            name = (o.metadata or {}).get("workflow_name") or "unknown"
            if name not in by_workflow:
                by_workflow[name] = {
                    "workflow_name": name,
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "total_duration_seconds": 0.0,
                }
            rec = by_workflow[name]
            rec["total"] += 1
            rec["total_duration_seconds"] += o.duration_seconds
            if o.success:
                rec["success_count"] += 1
            else:
                rec["failed_count"] += 1
        result = []
        for name, rec in by_workflow.items():
            total = rec["total"]
            result.append({
                "workflow_name": rec["workflow_name"],
                "total_executions": total,
                "success_count": rec["success_count"],
                "failed_count": rec["failed_count"],
                "success_rate": rec["success_count"] / total if total else 0,
                "avg_duration_seconds": rec["total_duration_seconds"] / total if total else 0,
            })
        return sorted(result, key=lambda x: -x["total_executions"])
    
    def get_all_agent_performance(self) -> Dict[str, AgentPerformance]:
        """Get performance metrics for all agents."""
        return dict(self._agent_stats)
    
    def get_common_errors(self, task_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common errors."""
        if task_type:
            errors = self._error_patterns.get(task_type, [])
        else:
            errors = []
            for task_errors in self._error_patterns.values():
                errors.extend(task_errors)
        
        # Count error occurrences
        error_counts: Dict[str, int] = defaultdict(int)
        for err in errors:
            error_key = err["error"][:100]
            error_counts[error_key] += 1
        
        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"error": err, "count": count}
            for err, count in sorted_errors[:limit]
        ]
    
    def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on outcomes."""
        suggestions = []
        
        # Find agents with low success rates
        for agent_id, perf in self._agent_stats.items():
            if perf.total_tasks >= 10 and perf.success_rate < 0.7:
                suggestions.append({
                    "type": "agent_improvement",
                    "agent_id": agent_id,
                    "current_success_rate": perf.success_rate,
                    "suggestion": f"Agent {agent_id} has {perf.success_rate:.0%} success rate. Consider reviewing its implementation.",
                    "common_errors": list(perf.common_errors.keys())[:3]
                })
        
        # Find task types without good approaches
        task_types_seen = set(o.task_type for o in self._outcomes)
        for task_type in task_types_seen:
            best = self.get_recommended_approach(task_type)
            if not best:
                task_outcomes = [o for o in self._outcomes if o.task_type == task_type]
                success_rate = sum(1 for o in task_outcomes if o.success) / len(task_outcomes)
                if success_rate < 0.6:
                    suggestions.append({
                        "type": "skill_needed",
                        "task_type": task_type,
                        "current_success_rate": success_rate,
                        "suggestion": f"No reliable approach for {task_type}. Consider creating a skill."
                    })
        
        # Find error patterns that keep repeating
        for task_type, errors in self._error_patterns.items():
            if len(errors) >= 5:
                recent_errors = errors[-10:]
                error_msgs = [e["error"][:50] for e in recent_errors]
                most_common = max(set(error_msgs), key=error_msgs.count)
                if error_msgs.count(most_common) >= 3:
                    suggestions.append({
                        "type": "recurring_error",
                        "task_type": task_type,
                        "error_pattern": most_common,
                        "suggestion": f"Recurring error in {task_type}. Consider auto-fix rule."
                    })
        
        return suggestions
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learning data."""
        return {
            "total_outcomes": len(self._outcomes),
            "patterns_learned": len(self._patterns),
            "agents_tracked": len(self._agent_stats),
            "overall_success_rate": sum(1 for o in self._outcomes if o.success) / len(self._outcomes) if self._outcomes else 0,
            "top_patterns": [
                {
                    "task_type": p.task_type,
                    "approach": p.successful_approach,
                    "success_rate": p.success_rate
                }
                for p in sorted(self._patterns.values(), key=lambda x: x.success_rate, reverse=True)[:5]
            ],
            "improvement_suggestions": self.get_improvement_suggestions()[:5]
        }
    
    def export_learning_report(self, output_path: Optional[str] = None) -> str:
        """Export learning report to file."""
        output_path = output_path or str(self._data_dir / "learning_report.json")
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_learning_summary(),
            "agent_performance": {
                agent_id: {
                    "total_tasks": p.total_tasks,
                    "success_rate": p.success_rate,
                    "avg_duration": p.avg_duration,
                    "common_errors": dict(list(p.common_errors.items())[:5])
                }
                for agent_id, p in self._agent_stats.items()
            },
            "patterns": {
                pid: {
                    "task_type": p.task_type,
                    "approach": p.successful_approach,
                    "success_rate": p.success_rate,
                    "sample_size": p.sample_size
                }
                for pid, p in self._patterns.items()
            },
            "common_errors": self.get_common_errors(limit=20)
        }
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Learning report exported to {output_path}")
        return output_path


# Singleton instance
_service: Optional[LearningFeedbackService] = None


def get_learning_service() -> LearningFeedbackService:
    """Get or create the singleton learning service."""
    global _service
    if _service is None:
        _service = LearningFeedbackService()
    return _service


def main():
    """Test the learning feedback service."""
    service = get_learning_service()
    
    # Record some test outcomes
    service.record_outcome(
        task_type="deploy_website",
        agent_id="deployer",
        success=True,
        duration_seconds=45.2,
        approach_used="docker_rebuild"
    )
    
    service.record_outcome(
        task_type="deploy_website",
        agent_id="deployer",
        success=True,
        duration_seconds=38.5,
        approach_used="docker_rebuild"
    )
    
    service.record_outcome(
        task_type="fix_lint_error",
        agent_id="code_auditor",
        success=False,
        duration_seconds=12.0,
        error_message="Could not determine fix",
        approach_used="auto_format"
    )
    
    # Get summary
    summary = service.get_learning_summary()
    
    print("\n=== Learning Summary ===")
    print(f"Total outcomes: {summary['total_outcomes']}")
    print(f"Patterns learned: {summary['patterns_learned']}")
    print(f"Overall success rate: {summary['overall_success_rate']:.0%}")
    
    if summary["improvement_suggestions"]:
        print("\nSuggestions:")
        for s in summary["improvement_suggestions"]:
            print(f"  - {s['suggestion']}")
    
    # Export report
    report_path = service.export_learning_report()
    print(f"\nReport exported to: {report_path}")


if __name__ == "__main__":
    main()
