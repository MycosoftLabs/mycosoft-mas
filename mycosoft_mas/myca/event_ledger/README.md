# MYCA Event Ledger

**Date:** February 17, 2026

## Purpose

The Event Ledger provides append-only logging of all tool calls, permission denials, and risk events for audit, analysis, and self-improvement.

## Event Structure

Events are stored as JSONL (JSON Lines) format, one event per line:

```json
{
  "ts": 1708200000,
  "session_id": "abc-123",
  "agent": "dev_agent",
  "tool": "file_editor",
  "args_hash": "sha256:abc123...",
  "result_status": "success",
  "elapsed_ms": 150,
  "error_class": null,
  "risk_flags": [],
  "artifacts": ["path/to/file.py"]
}
```

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `ts` | int | Unix timestamp |
| `session_id` | string | Current session identifier |
| `agent` | string | Agent that initiated the call |
| `tool` | string | Tool name |
| `args_hash` | string | SHA256 hash of arguments (NOT full args for privacy) |
| `result_status` | string | success, error, denied, timeout |
| `elapsed_ms` | int | Execution time in milliseconds |
| `error_class` | string | Error type if failed, null otherwise |
| `risk_flags` | array | List of risk indicators |
| `artifacts` | array | Files/resources affected |

## Risk Flags

| Flag | Meaning |
|------|---------|
| `injection_attempt` | External content tried to override instructions |
| `secret_attempt` | Attempted to access/output secrets |
| `path_denied` | Tried to access forbidden path |
| `network_denied` | Tried network access without permission |
| `sandbox_violation` | Code tried to escape sandbox |
| `timeout` | Operation exceeded time limit |
| `high_risk_approved` | High-risk action was explicitly approved |

## Storage

Events are stored in:
- `mycosoft_mas/myca/event_ledger/events.jsonl` (current day)
- Rotated daily to `events_YYYYMMDD.jsonl`

## Usage

```python
from mycosoft_mas.myca.event_ledger.ledger_writer import EventLedger

ledger = EventLedger()

# Log a successful tool call
ledger.log_tool_call(
    agent="dev_agent",
    tool_name="file_editor",
    args_hash="sha256:abc123",
    result_status="success",
    elapsed_ms=150,
    artifacts=["path/to/file.py"]
)

# Log a denied action
ledger.log_tool_call(
    agent="dev_agent",
    tool_name="exec_shell",
    args_hash="sha256:def456",
    result_status="denied",
    risk_flags=["path_denied"]
)
```

## Analysis

The Critic agent periodically analyzes the ledger to:
1. Identify recurring failures
2. Detect permission gaps (legitimate use blocked)
3. Flag security anomalies
4. Propose improvements

## Retention

- Current day: Always available
- Last 7 days: Full detail
- Last 30 days: Aggregated stats
- Older: Archived to cold storage

## Privacy

- Full argument values are NEVER logged
- Only SHA256 hash of arguments is stored
- Secrets are NEVER present in logs
- User identifiers are pseudonymized
