# Manager Agent Memory

**Version:** 1.0.0  
**Date:** February 17, 2026

## Memory Types

### Short-Term Memory (Session)

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `current_tasks` | Dict[str, Task] | Session | Active task tracking |
| `agent_states` | Dict[str, AgentState] | Session | Agent availability |
| `pending_escalations` | List[Escalation] | Session | Awaiting human |
| `ci_status_cache` | Dict[str, CIResult] | 5 min | CI results cache |

### Long-Term Memory (Persistent)

| Key | Type | Storage | Purpose |
|-----|------|---------|---------|
| `task_history` | List[CompletedTask] | MINDEX | Historical tasks |
| `agent_performance` | Dict[str, Metrics] | MINDEX | Performance tracking |
| `escalation_patterns` | Dict[str, int] | MINDEX | Escalation trends |
| `improvement_stats` | Stats | MINDEX | Overall statistics |

## Memory Schema

### Task Record
```python
@dataclass
class TaskRecord:
    task_id: str
    proposal_id: str
    agent_type: str
    agent_id: str
    status: str
    created_at: datetime
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    retries: int
    result: Optional[dict]
```

### Agent Performance
```python
@dataclass
class AgentPerformance:
    agent_type: str
    tasks_completed: int
    tasks_failed: int
    average_duration: float
    success_rate: float
    last_task: datetime
    current_load: int
```

## Memory Operations

### Remember Task
```python
async def remember_task(task: Task):
    # Short-term
    current_tasks[task.id] = task
    
    # Long-term (on completion)
    if task.is_complete:
        await mindex.store(
            collection="myca_tasks",
            document=task.to_record()
        )
```

### Recall Similar Tasks
```python
async def recall_similar_tasks(description: str) -> List[TaskRecord]:
    return await mindex.semantic_search(
        collection="myca_tasks",
        query=description,
        top_k=5
    )
```

### Update Agent Performance
```python
async def update_performance(agent_type: str, task_result: TaskResult):
    perf = agent_performance.get(agent_type, AgentPerformance())
    perf.tasks_completed += 1 if task_result.success else 0
    perf.tasks_failed += 0 if task_result.success else 1
    perf.average_duration = rolling_average(
        perf.average_duration,
        task_result.duration
    )
    agent_performance[agent_type] = perf
```

## Context Injection

When starting a new task, inject relevant context:

```python
def get_task_context(proposal: Proposal) -> dict:
    return {
        "similar_tasks": recall_similar_tasks(proposal.description),
        "agent_availability": get_available_agents(),
        "current_load": get_system_load(),
        "recent_failures": get_recent_failures(hours=24),
    }
```

## Memory Limits

| Memory Type | Limit | Eviction |
|-------------|-------|----------|
| Session tasks | 100 | LRU |
| CI cache | 50 | TTL |
| Task history query | 1000 | By date |
| Performance stats | Per agent type | Rolling window |

## Privacy Considerations

- NEVER store actual code in memory
- Hash sensitive arguments before storage
- Purge memory on security incident
- Respect retention policies
