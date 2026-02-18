# Output Standards

**Date:** February 17, 2026
**Status:** Active
**Version:** 1.0.0

## Purpose

This document defines output format requirements for all MYCA agents to ensure consistency, actionability, and auditability.

## General Principles

### 1. Prefer Structured Formats
Use checklists, file trees, patches, and acceptance criteria over prose.

### 2. Be Specific
Provide exact filenames, line numbers, and commands. Avoid vague references.

### 3. Be Actionable
Every output should include clear next steps that can be executed immediately.

### 4. Be Auditable
Include enough context for later review and rollback if needed.

## Output Formats by Type

### Code Changes

When proposing code changes, include:

```markdown
## File: path/to/file.py
## Lines: 45-52
## Action: Replace

### Before
```python
def old_function():
    pass
```

### After
```python
def new_function():
    return True
```

### Reason
Brief explanation of why this change is needed.
```

### Task Breakdown

When breaking down tasks:

```markdown
## Task: [Task Name]

### Subtasks
- [ ] Step 1: Description (Owner: agent_name)
- [ ] Step 2: Description (Owner: agent_name)
- [ ] Step 3: Description (Owner: agent_name)

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Artifacts
- File 1: path/to/file1.py
- File 2: path/to/file2.py
```

### Implementation Steps

When providing implementation instructions:

```markdown
## Step 1: [Step Name]

### Command
```bash
pip install package-name
```

### Expected Output
```
Successfully installed package-name-1.0.0
```

### Verification
```bash
python -c "import package; print(package.__version__)"
```
```

### Error Reports

When reporting errors:

```markdown
## Error: [Error Title]

### Summary
Brief description of what went wrong.

### Stack Trace
```
Traceback (most recent call last):
  File "path/to/file.py", line 42, in function
    ...
ErrorType: error message
```

### Root Cause
Analysis of why this error occurred.

### Resolution
Steps to fix the error.

### Prevention
How to prevent this error in the future.
```

### Improvement Proposals

When proposing improvements (for Critic agent):

```markdown
## Improvement: [Title]

### Problem Statement
What issue was observed.

### Evidence
- Event Ledger ID: abc123
- Eval failure: prompt_injection_test_2
- Error rate: 15% over last 24 hours

### Proposed Patch
Files to be changed:
- `path/to/file1.py`: Add input validation
- `path/to/file2.py`: Update error handling

### Diff
```diff
- old_code()
+ new_code()
```

### Evals Added
- `evals/golden_tasks/new_test.md`: Tests the fix

### Rollback Plan
If this change causes issues:
1. Revert commit xyz
2. Restart service
```

## Forbidden in Output

### Never Include

| Category | Examples |
|----------|----------|
| Secrets | API keys, tokens, passwords, SSH keys |
| Internal URLs | Admin panels, internal APIs, database URLs |
| Personal Data | Emails, phone numbers, addresses |
| Credentials | Usernames + passwords together |
| Session Data | Session IDs, auth cookies |

### If You Must Reference Secrets

Use placeholder notation:
```
API_KEY=<REDACTED:api_key_for_service_x>
DATABASE_URL=<REDACTED:postgres_connection_string>
```

## Uncertainty Handling

When uncertain:

```markdown
## Assumptions
- Assumption 1: [What you're assuming]
- Assumption 2: [What you're assuming]

## Questions
Before proceeding, please clarify:
1. Question about ambiguous requirement
2. Question about edge case

## Safe Default
If no clarification is provided, I will:
- Take the safest/most conservative action
- Log the decision for review
```

## File Naming

When creating files:

| Type | Format | Example |
|------|--------|---------|
| Documentation | `TOPIC_MMMDD_YYYY.md` | `DEPLOYMENT_FEB17_2026.md` |
| Scripts | `snake_case.py` | `validate_permissions.py` |
| Config | `lowercase.json` | `permissions.json` |
| Tests | `test_feature.py` | `test_skill_lint.py` |

## Validation

Before finalizing output:

1. **Check for secrets** - Scan output for patterns like `AKIA`, `-----BEGIN`, `token=`
2. **Check for paths** - Ensure all file paths are valid and accessible
3. **Check for commands** - Ensure all commands are safe and correct
4. **Check for completeness** - Ensure all referenced files/steps are included
