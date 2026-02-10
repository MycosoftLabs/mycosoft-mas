# Self-Healing MAS Infrastructure

**Created:** February 9, 2026  
**Status:** Implemented  
**Author:** MYCA Autonomous Coding System

## Overview

The Self-Healing MAS Infrastructure enables the Mycosoft Multi-Agent System to:
1. **Orchestrator can tell agents to write code** - MYCA can direct coding tasks
2. **Agents can adjust and change code as needed** - Any agent can request fixes
3. **All code modifications are monitored** - SecurityCodeReviewer gates all changes
4. **Security agents monitor for vulnerabilities** - Real-time CVE and OWASP scanning

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MYCA Orchestrator                           │
│  ┌────────────────────┐    ┌─────────────────────────────────────┐ │
│  │ request_code_fix() │    │ tell_agent_to_code()                │ │
│  │ halt_all_changes() │    │ get_code_change_status()            │ │
│  └─────────┬──────────┘    └──────────────────┬──────────────────┘ │
└────────────┼───────────────────────────────────┼────────────────────┘
             │                                   │
             ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CodeModificationService                          │
│  Central hub for all code change requests                           │
│  - Validates with SecurityCodeReviewer                              │
│  - Routes to CodingAgent                                            │
│  - Tracks audit log                                                 │
│  - Enforces budget limits ($5/request)                              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SecurityCodeReviewer                             │
│  Pre-execution security gate                                        │
│  - Secret detection (API keys, passwords)                           │
│  - Protected file enforcement                                       │
│  - SQL injection pattern detection                                  │
│  - Dangerous code pattern detection                                 │
│  APPROVE / BLOCK decision                                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
┌──────────────────────┐              ┌──────────────────────────────┐
│ If BLOCKED:          │              │ If APPROVED:                 │
│ - Log to Guardian    │              │ - Execute via CodingAgent    │
│ - Notify orchestrator│              │ - Post-scan for vulns        │
│ - Reject request     │              │ - Create PR or commit        │
└──────────────────────┘              └──────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SelfHealingMonitor                               │
│  Continuous system health monitoring                                │
│  - Watches for agent errors/crashes                                 │
│  - Monitors test failures                                           │
│  - Tracks API endpoint failures                                     │
│  - Auto-triggers fixes after ERROR_THRESHOLD (3) occurrences        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VulnerabilityScanner                             │
│  Real-time security scanning                                        │
│  - OWASP Top 10 pattern detection                                   │
│  - CVE scanning via safety package                                  │
│  - Secret detection in code                                         │
│  - Reports critical issues to SelfHealingMonitor                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Components Created

### 1. SecurityCodeReviewer
**File:** `mycosoft_mas/security/code_reviewer.py`

Reviews ALL code changes before execution:
- Scans for hardcoded secrets (Anthropic, OpenAI, GitHub, Slack, AWS keys)
- Validates no protected files are modified
- Checks for SQL injection patterns
- Detects dangerous patterns (rm -rf, DROP TABLE, eval, exec)
- Returns approve/block decision with risk level

**Protected Files (cannot be modified by automation):**
- `mycosoft_mas/core/orchestrator.py`
- `mycosoft_mas/core/orchestrator_service.py`
- `mycosoft_mas/safety/guardian_agent.py`
- `mycosoft_mas/security/*`
- `.env*`, `secrets.json`, `credentials.json`

### 2. CodeModificationService
**File:** `mycosoft_mas/services/code_modification_service.py`

Central hub for all code change requests:
- Receives requests from orchestrator or any agent
- Validates with SecurityCodeReviewer
- Routes approved changes to CodingAgent
- Tracks all modifications in audit log
- Enforces budget limit: $5 per request

### 3. Coding API Router
**File:** `mycosoft_mas/core/routers/coding_api.py`

REST API endpoints:
- `POST /api/code/request` - Request code change
- `GET /api/code/status/{id}` - Get change status
- `GET /api/code/history` - View change history
- `POST /api/code/approve/{id}` - Manual approval override
- `POST /api/code/cancel/{id}` - Cancel pending request
- `POST /api/code/halt` - Emergency halt all changes
- `POST /api/code/security/scan` - Run security scan
- `GET /api/code/security/stats` - Security review statistics
- `GET /api/code/health` - System health check

### 4. OrchestratorService Integration
**File:** `mycosoft_mas/core/orchestrator_service.py`

New orchestrator methods:
```python
async def request_code_fix(description, target_files, priority, context)
async def tell_agent_to_code(agent_id, coding_task, target_files, priority)
async def get_code_change_status(change_id)
async def halt_all_code_changes()
```

New API endpoints:
- `POST /code/fix` - Request a code fix
- `POST /code/tell-agent` - Tell agent to code
- `GET /code/status/{id}` - Get change status
- `POST /code/halt` - Emergency halt

### 5. BaseAgent Integration
**File:** `mycosoft_mas/agents/base_agent.py`

New methods available to ALL agents:
```python
async def request_code_change(description, reason, target_files, priority)
async def request_self_improvement(improvement_description, priority)
async def report_bug_for_fix(error_message, stack_trace, affected_files)
```

### 6. SelfHealingMonitor
**File:** `mycosoft_mas/services/self_healing_monitor.py`

Continuous health monitoring:
- Tracks test failures
- Monitors agent errors/crashes
- Watches API endpoint failures
- Auto-triggers fixes after 3 occurrences of same error
- Immediate fix for critical issues (crashes, security vulns)

### 7. VulnerabilityScanner
**File:** `mycosoft_mas/security/vulnerability_scanner.py`

Real-time vulnerability scanning:
- OWASP Top 10 pattern detection
- CVE scanning via `safety` package
- Secret detection in code
- Continuous monitoring mode
- Reports to SelfHealingMonitor

## Usage Examples

### Orchestrator Requesting a Code Fix
```python
orchestrator = OrchestratorService()
result = await orchestrator.request_code_fix(
    description="Fix the memory leak in data_processor.py",
    target_files=["mycosoft_mas/services/data_processor.py"],
    priority=7,
    context={"error": "Memory usage growing unbounded"}
)
print(f"Fix request submitted: {result['change_id']}")
```

### Orchestrator Telling an Agent to Code
```python
result = await orchestrator.tell_agent_to_code(
    agent_id="coding_agent",
    coding_task="Add input validation to all API endpoints",
    priority=6
)
```

### Agent Requesting Self-Improvement
```python
class MyAgent(BaseAgent):
    async def process(self):
        # Agent identifies a way to improve itself
        await self.request_self_improvement(
            improvement_description="Add caching to reduce API calls",
            priority=3
        )
```

### Agent Reporting a Bug
```python
class MyAgent(BaseAgent):
    async def process(self):
        try:
            await self.do_something()
        except Exception as e:
            await self.report_bug_for_fix(
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                affected_files=["mycosoft_mas/agents/my_agent.py"]
            )
```

### API Usage
```bash
# Request a code fix
curl -X POST http://192.168.0.188:8001/api/code/request \
  -H "Content-Type: application/json" \
  -d '{
    "requester_id": "operator",
    "change_type": "fix_bug",
    "description": "Fix the database connection pool leak",
    "target_files": ["mycosoft_mas/services/database.py"],
    "priority": 8
  }'

# Check status
curl http://192.168.0.188:8001/api/code/status/abc123

# Run security scan
curl -X POST http://192.168.0.188:8001/api/code/security/scan \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["mycosoft_mas/agents/"]}'

# Emergency halt
curl -X POST http://192.168.0.188:8001/api/code/halt
```

## Safety Constraints

1. **Protected Files** - Core system files cannot be modified by automation
2. **Security Review** - ALL changes pass through SecurityCodeReviewer
3. **Budget Limit** - $5 maximum per code change request
4. **PR Required** - Changes to `core/*`, `agents/__init__.py`, `myca_main.py` require PR
5. **Audit Trail** - All changes logged with full context
6. **Emergency Halt** - GuardianAgent or operator can halt all changes instantly
7. **Post-Execution Scan** - Generated code is scanned for vulnerabilities
8. **Rollback Capability** - Changes with security issues are rolled back

## Integration Points

- **CodingAgent** - Executes approved code changes
- **LocalClaudeRouter** - Routes to VM or local Claude Code instances
- **GuardianAgent** - Receives alerts on blocked changes
- **SecurityMonitor** - Logs security events
- **Memory System** - Agents remember their code change requests

## Monitoring

The SelfHealingMonitor provides statistics:
```python
monitor = await get_self_healing_monitor()
stats = monitor.get_stats()
# {
#   "is_running": True,
#   "issues_detected": 42,
#   "fixes_triggered": 5,
#   "fixes_successful": 4,
#   "pending_fixes": 1,
#   "unique_errors": 12,
#   "last_check": "2026-02-09T15:30:00"
# }
```

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `mycosoft_mas/security/code_reviewer.py` | Created | Security gate for code changes |
| `mycosoft_mas/services/code_modification_service.py` | Created | Central code change hub |
| `mycosoft_mas/core/routers/coding_api.py` | Created | REST API for code modifications |
| `mycosoft_mas/core/orchestrator_service.py` | Modified | Added code change methods |
| `mycosoft_mas/agents/base_agent.py` | Modified | Added agent code change methods |
| `mycosoft_mas/services/self_healing_monitor.py` | Created | Automatic issue detection |
| `mycosoft_mas/security/vulnerability_scanner.py` | Created | Real-time vulnerability scanning |

## Next Steps

1. **Deploy to MAS VM** - Restart orchestrator to load new components
2. **Test the flow** - Submit a test code change request
3. **Configure monitoring** - Start SelfHealingMonitor as background service
4. **Add to n8n** - Create workflows for code change notifications
5. **Dashboard** - Add UI for monitoring code changes on website
