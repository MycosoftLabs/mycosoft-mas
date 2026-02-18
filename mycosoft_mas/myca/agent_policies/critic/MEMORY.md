# Critic Agent Memory

**Version:** 1.0.0  
**Date:** February 17, 2026

## Memory Types

### Short-Term Memory (Session)

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `current_failures` | List[Failure] | Session | Active failure analysis |
| `patch_drafts` | Dict[str, Patch] | Session | In-progress patches |
| `test_results_cache` | Dict[str, TestResult] | 10 min | Recent test runs |
| `code_context` | Dict[str, str] | Session | Relevant code snippets |

### Long-Term Memory (Persistent)

| Key | Type | Storage | Purpose |
|-----|------|---------|---------|
| `failure_patterns` | List[Pattern] | MINDEX | Historical failure patterns |
| `patch_history` | List[PatchRecord] | MINDEX | All generated patches |
| `root_causes` | Dict[str, List[str]] | MINDEX | Common root causes by category |
| `regression_tests` | List[TestCase] | MINDEX | All added regression tests |

## Memory Schema

### Failure Record
```python
@dataclass
class FailureRecord:
    failure_id: str
    category: str  # test, eval, runtime
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    affected_files: List[str]
    root_cause: Optional[str]
    patch_id: Optional[str]
    regression_test_id: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
```

### Patch Record
```python
@dataclass
class PatchRecord:
    patch_id: str
    failure_id: str
    file_path: str
    diff: str
    description: str
    created_at: datetime
    status: str  # draft, submitted, merged, rejected
    regression_test_id: Optional[str]
    ci_result: Optional[str]
```

### Pattern Record
```python
@dataclass
class PatternRecord:
    pattern_id: str
    description: str
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    common_factors: dict
    resolution: Optional[str]
    is_systemic: bool
```

## Memory Operations

### Remember Failure
```python
async def remember_failure(failure: Failure):
    # Short-term for active analysis
    current_failures.append(failure)
    
    # Long-term after resolution
    await mindex.store(
        collection="myca_failures",
        document=failure.to_record()
    )
```

### Recall Similar Failures
```python
async def recall_similar_failures(error: str) -> List[FailureRecord]:
    return await mindex.semantic_search(
        collection="myca_failures",
        query=error,
        top_k=5,
        filters={"resolved": True}  # Learn from resolved
    )
```

### Remember Patch
```python
async def remember_patch(patch: Patch, failure: Failure):
    record = PatchRecord(
        patch_id=generate_id(),
        failure_id=failure.id,
        file_path=patch.file,
        diff=patch.to_diff(),
        description=patch.description,
        created_at=datetime.utcnow(),
        status="draft"
    )
    
    patch_drafts[record.patch_id] = record
    
    # Persist when submitted
    if patch.status == "submitted":
        await mindex.store(
            collection="myca_patches",
            document=record
        )
```

### Learn Pattern
```python
async def learn_pattern(failures: List[Failure]):
    # Cluster failures
    pattern = extract_pattern(failures)
    
    # Check if pattern exists
    existing = await mindex.query(
        collection="myca_patterns",
        filter={"description": {"$similar": pattern.description}}
    )
    
    if existing:
        # Update occurrence count
        await mindex.update(
            collection="myca_patterns",
            id=existing[0].id,
            update={"occurrences": existing[0].occurrences + 1}
        )
    else:
        # Store new pattern
        await mindex.store(
            collection="myca_patterns",
            document=pattern.to_record()
        )
```

## Context Injection

When analyzing a failure, inject relevant context:

```python
def get_failure_context(failure: Failure) -> dict:
    return {
        "similar_failures": recall_similar_failures(failure.error),
        "related_patches": recall_patches_for_file(failure.file),
        "known_patterns": get_patterns_for_error(failure.error_type),
        "code_snippet": get_code_around_failure(failure),
    }
```

## Memory Limits

| Memory Type | Limit | Eviction |
|-------------|-------|----------|
| Current failures | 50 | FIFO |
| Patch drafts | 20 | LRU |
| Test results cache | 100 | TTL |
| Pattern queries | 100 | By relevance |

## Learning Feedback

After a patch is merged successfully:
```python
async def reinforce_success(patch_id: str):
    patch = await get_patch(patch_id)
    failure = await get_failure(patch.failure_id)
    
    # Store root cause → fix mapping
    await learn_root_cause_fix(
        error_type=failure.error_type,
        root_cause=failure.root_cause,
        fix_pattern=extract_fix_pattern(patch)
    )
```

## Privacy Considerations

- Hash sensitive error content
- Do not store full stack traces with secrets
- Purge code context after analysis
- Respect data retention policies
