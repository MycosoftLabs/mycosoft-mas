# MINDEX ETL Scheduler Fix

**Date**: 2026-01-16  
**Issue**: ETL container showing "unhealthy" status  
**Root Cause**: Type comparison error in scheduler.py

---

## Problem Description

The MINDEX ETL container (`mycosoft-always-on-mindex-etl-1`) is reporting unhealthy status due to errors in the scheduler:

### Error Logs

```
2026-01-16 21:39:15,259 [ERROR] mindex_scheduler: Scheduler error: '>=' not supported between instances of 'dict' and 'int'
Traceback (most recent call last):
  File "/app/mindex_etl/scheduler.py", line 95, in run_daemon
    total = sum(v for v in results.values() if v >= 0)
TypeError: '>=' not supported between instances of 'dict' and 'int'

2026-01-16 22:39:15,564 [ERROR] mindex_scheduler: Job mycobank failed: sync_mycobank_taxa() got an unexpected keyword argument 'max_pages'
TypeError: sync_mycobank_taxa() got an unexpected keyword argument 'max_pages'
```

---

## Root Cause Analysis

### Issue 1: Type Comparison Error

In `scheduler.py` line 95, the code attempts to sum job results:

```python
total = sum(v for v in results.values() if v >= 0)
```

However, some jobs are returning a `dict` instead of an `int`, causing the type comparison error.

### Issue 2: Function Signature Mismatch

The `sync_mycobank_taxa()` function does not accept a `max_pages` keyword argument, but the scheduler is passing it.

---

## Fix Required

### Fix 1: scheduler.py line 95

**Before:**
```python
total = sum(v for v in results.values() if v >= 0)
```

**After:**
```python
total = sum(v for v in results.values() if isinstance(v, (int, float)) and v >= 0)
```

### Fix 2: Job run function in run_all.py

**Before:**
```python
count = job.run(max_pages=max_pages)
```

**After:**
```python
# Check if function accepts max_pages
import inspect
sig = inspect.signature(job.run_func)
if 'max_pages' in sig.parameters:
    count = job.run(max_pages=max_pages)
else:
    count = job.run()
```

---

## File Locations

The files that need modification are located in:

```
WEBSITE/website/services/mindex-etl/mindex_etl/
├── scheduler.py        # Line 95 - type check fix
└── jobs/
    └── run_all.py      # Job execution - signature check
```

---

## Temporary Workaround

Until the fix is applied, the ETL container will continue to show as unhealthy but the data pipeline will still function for most jobs. The GBIF job is completing successfully:

```
2026-01-16 21:39:15,259 [INFO] mindex_scheduler: Job gbif completed: 0 records
```

---

## Impact Assessment

| Impact | Severity | Description |
|--------|----------|-------------|
| ETL Health | Medium | Container shows unhealthy |
| Data Pipeline | Low | Most jobs still complete |
| CREP Dashboard | None | Cached data still serves |
| Monitoring | Low | Alerts may fire unnecessarily |

---

## Action Items

1. [ ] Apply type check fix to scheduler.py
2. [ ] Apply signature check to run_all.py
3. [ ] Rebuild MINDEX ETL container
4. [ ] Verify health check passes
5. [ ] Monitor for any remaining errors

---

## Verification

After applying fixes:

```bash
# Check container health
docker ps | findstr mindex-etl

# Check logs for errors
docker logs mycosoft-always-on-mindex-etl-1 --tail 20

# Expected: No TypeError messages
```

---

*Document created: 2026-01-16*
