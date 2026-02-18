# Dev Agent Memory

**Version:** 1.0.0  
**Date:** February 17, 2026

## Memory Types

### Short-Term Memory (Session)

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `current_task` | Task | Session | Active task details |
| `code_context` | Dict[str, str] | Session | Relevant code snippets |
| `test_results` | List[TestResult] | Session | Recent test runs |
| `file_changes` | Dict[str, Change] | Session | Uncommitted changes |

### Long-Term Memory (Persistent)

| Key | Type | Storage | Purpose |
|-----|------|---------|---------|
| `code_patterns` | List[Pattern] | MINDEX | Learned code patterns |
| `task_history` | List[TaskRecord] | MINDEX | Completed tasks |
| `common_errors` | Dict[str, Fix] | MINDEX | Error → fix mappings |
| `test_patterns` | List[TestPattern] | MINDEX | Test writing patterns |

## Memory Schema

### Task Record
```python
@dataclass
class DevTaskRecord:
    task_id: str
    type: str  # feature, bugfix, refactor, test, docs
    description: str
    files_modified: List[str]
    lines_added: int
    lines_removed: int
    tests_added: int
    duration_seconds: int
    pr_id: Optional[str]
    outcome: str  # success, failed, cancelled
    created_at: datetime
    completed_at: Optional[datetime]
```

### Code Pattern
```python
@dataclass
class CodePattern:
    pattern_id: str
    name: str
    description: str
    example_code: str
    use_cases: List[str]
    anti_patterns: List[str]
    frequency: int  # How often used
    last_used: datetime
```

### Error Fix Mapping
```python
@dataclass
class ErrorFix:
    error_pattern: str  # Regex or key phrase
    error_type: str
    common_causes: List[str]
    fixes: List[str]
    example_fix: str
    success_count: int
```

## Memory Operations

### Remember Task
```python
async def remember_task(task: Task, outcome: str):
    record = DevTaskRecord(
        task_id=task.id,
        type=task.type,
        description=task.description,
        files_modified=task.files_modified,
        lines_added=count_additions(),
        lines_removed=count_deletions(),
        tests_added=count_new_tests(),
        duration_seconds=task.duration,
        pr_id=task.pr_id,
        outcome=outcome,
        created_at=task.created_at,
        completed_at=datetime.utcnow(),
    )
    
    await mindex.store(
        collection="myca_dev_tasks",
        document=record
    )
```

### Recall Similar Code
```python
async def recall_similar_code(description: str) -> List[CodePattern]:
    return await mindex.semantic_search(
        collection="myca_code_patterns",
        query=description,
        top_k=5
    )
```

### Learn Code Pattern
```python
async def learn_code_pattern(code: str, context: str):
    # Extract pattern
    pattern = CodePattern(
        pattern_id=generate_id(),
        name=extract_pattern_name(code),
        description=context,
        example_code=code,
        use_cases=[context],
        anti_patterns=[],
        frequency=1,
        last_used=datetime.utcnow(),
    )
    
    # Check if similar exists
    existing = await recall_similar_code(pattern.description)
    
    if existing and is_same_pattern(existing[0], pattern):
        # Reinforce existing
        await update_pattern_frequency(existing[0].pattern_id)
    else:
        # Store new
        await mindex.store(
            collection="myca_code_patterns",
            document=pattern
        )
```

### Remember Error Fix
```python
async def remember_error_fix(error: str, fix: str, success: bool):
    error_type = classify_error(error)
    
    existing = await mindex.query(
        collection="myca_error_fixes",
        filter={"error_type": error_type}
    )
    
    if existing:
        # Update with new fix
        if success:
            await mindex.update(
                collection="myca_error_fixes",
                id=existing[0].id,
                update={
                    "fixes": existing[0].fixes + [fix],
                    "success_count": existing[0].success_count + 1
                }
            )
    else:
        # Create new mapping
        await mindex.store(
            collection="myca_error_fixes",
            document=ErrorFix(
                error_pattern=extract_error_pattern(error),
                error_type=error_type,
                common_causes=[extract_cause(error)],
                fixes=[fix],
                example_fix=fix,
                success_count=1 if success else 0,
            )
        )
```

## Context Injection

When starting a coding task:

```python
def get_coding_context(task: Task) -> dict:
    return {
        "similar_tasks": recall_similar_tasks(task.description),
        "relevant_patterns": recall_similar_code(task.description),
        "file_history": get_file_modification_history(task.files),
        "common_errors": get_common_errors_for_area(task.area),
        "test_patterns": get_test_patterns_for_area(task.area),
    }
```

## Memory Limits

| Memory Type | Limit | Eviction |
|-------------|-------|----------|
| Code context | 50 files | LRU |
| Test results | 100 | FIFO |
| File changes | Session | Clear on commit |
| Pattern queries | 100 | By relevance |

## Privacy Considerations

- NEVER store actual secret values in code context
- Hash sensitive file paths
- Do not persist file contents long-term
- Respect .gitignore patterns
