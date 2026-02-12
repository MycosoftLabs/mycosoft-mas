# Start the Autonomous Learning System

**Created:** February 12, 2026

## Quick Start

### 1. Test MCP Servers (in Cursor)
MCP servers only work when you're chatting with me in Cursor. Try these:

```
Ask me: "Use the mycosoft-tasks MCP to scan for gaps in the codebase"
Ask me: "Use the mycosoft-orchestrator MCP to check system health"
Ask me: "Use the mycosoft-registry MCP to list all registered agents"
```

The MCPs are tools I use during our conversations. They're **passive** until you ask me to use them.

### 2. Run a One-Time Improvement Cycle

```powershell
# This will run once and show you a report
python scripts/start_autonomous_cursor.py --improvement
```

This will:
- Scan for TODOs/FIXMEs/stubs
- Look for code patterns
- Suggest new skills
- Generate a report in `data/improvement_report.json`

### 3. Start the Autonomous Scheduler (Background Daemon)

```powershell
# This runs in the background and auto-triggers tasks
python scripts/start_autonomous_cursor.py --scheduler
```

This will:
- Watch for file changes (Python, markdown, etc.)
- Auto-run linting when you edit Python files
- Auto-run tests when you edit test files
- Auto-sync registries when you add agents/skills
- Run pattern scans daily
- Run skill generation daily

**Press Ctrl+C to stop it.**

### 4. Check What It Learned

```powershell
# View the improvement report
cat data/improvement_report.json

# View learning feedback
cat data/learning_feedback.json

# View deployment tracking
cat data/deployment_feedback.json
```

## What "Learning" Means

The system learns in 3 ways:

### 1. Pattern Learning (Code Analysis)
- Scans all Python files across repos
- Finds repeated patterns (functions, classes, API routes)
- Suggests new skills when patterns are frequent enough
- **Runs:** When you run `--improvement` or automatically daily if scheduler is running

### 2. Outcome Learning (Task Tracking)
- Every time I complete a task for you, the outcome is recorded
- Success/failure/duration/errors are tracked
- Over time, identifies which approaches work best
- **Runs:** When I explicitly record outcomes during our conversation

### 3. Deployment Learning (Operations)
- Tracks every deployment (to MAS/MINDEX/WEBSITE VMs)
- Monitors health checks after deployment
- Learns failure patterns and suggests rollbacks
- **Runs:** When you deploy via the deployment scripts

## How to See Learning in Action

### Option A: Watch It Work (Interactive)

1. **Start the scheduler in one terminal:**
   ```powershell
   python scripts/start_autonomous_cursor.py --scheduler
   ```

2. **Edit a Python file in another terminal:**
   ```powershell
   # Make a small change to any Python file
   echo "# test comment" >> mycosoft_mas/agents/base_agent.py
   ```

3. **Watch the scheduler detect it and auto-run linting**

### Option B: Run Improvement Cycle Now

```powershell
# Run once and see the report
python scripts/start_autonomous_cursor.py --improvement
```

This will show you:
- How many gaps found (TODOs, stubs, etc.)
- How many patterns detected
- How many skills suggested

### Option C: Test MCP Tools in Our Conversation

Ask me right now:
- "Scan the codebase for gaps using the tasks MCP"
- "Check system health using the orchestrator MCP"
- "Show me all registered agents using the registry MCP"

## What Happens Automatically (If Scheduler Is Running)

| Trigger | What Happens |
|---------|--------------|
| You edit a .py file | Auto-lint with black/isort |
| You edit a test file | Auto-run the tests |
| You edit a .md file | Auto-rebuild docs |
| You add an agent | Auto-sync registries |
| You add a skill | Auto-sync registries |
| Daily at 3 AM | Full pattern scan + skill generation |
| Daily at 4 AM | Gap scan + improvement report |

## Is It Learning Right Now?

**Short answer: Not yet.**

The system is **installed** but **idle**. To start learning:

1. **For immediate learning:** Run `python scripts/start_autonomous_cursor.py --improvement`
2. **For continuous learning:** Run `python scripts/start_autonomous_cursor.py --scheduler` (leave it running)
3. **For conversation-based learning:** Just ask me to use the MCP tools during our chat

## Next Steps

1. **Test it:** Run `--improvement` once to see it work
2. **Deploy it:** Add the scheduler to Windows Task Scheduler to run at startup
3. **Use it:** Ask me to use MCP tools during our conversations

## Troubleshooting

**"No module named 'mycosoft_mas'"**
- The status check script can't import when run standalone
- This is fine - the actual MCP servers work when Cursor loads them

**"Data files not created yet"**
- Normal - they're created when the system first runs
- Run `--improvement` once to create them

**"MCP tools not working"**
- Restart Cursor IDE to reload `.mcp.json`
- Check Cursor logs: View > Output > MCP
