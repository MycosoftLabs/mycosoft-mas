# Skill Lint Rules

**Date:** February 17, 2026
**Version:** 1.0.0

## Purpose

This document defines the linting rules enforced by `scripts/myca_skill_lint.py` for all skill PERMISSIONS.json files.

## Required Files

Every skill directory must contain:
1. `PERMISSIONS.json` - Permission manifest (required)
2. `SKILL.md` - Skill documentation (optional but recommended)

## Validation Rules

### Rule 1: Schema Compliance
PERMISSIONS.json must validate against `_schema/PERMISSIONS.schema.json`.

**Check:** All required fields present with correct types.

### Rule 2: Risk Tier Consistency

| Risk Tier | Sandbox Required | Network Allowed | Max Runtime |
|-----------|-----------------|-----------------|-------------|
| low | optional | no | 60s |
| medium | optional | with allowlist | 120s |
| high | **yes** | with allowlist | 300s |
| critical | **yes** | only specific | 600s |

**Check:** `high` and `critical` risk skills MUST have `sandbox_required: true`.

### Rule 3: Network Allowlist
If `network.enabled` is `true`, `network.allowlist` MUST NOT be empty.

**Check:** Fail if network enabled but allowlist is empty.

### Rule 4: Deny Path Coverage
The following paths MUST be in `filesystem.deny_paths`:
- `~/.ssh`
- `~/.aws`
- `~/.config`
- `/etc`
- `/var`
- `/proc`

**Check:** Warn if standard sensitive paths not denied.

### Rule 5: Forbidden Strings
The following strings must NOT appear in `SKILL.md` or related files:
- `curl | bash`
- `wget | sh`
- `Ignore previous instructions`
- `paste your token`
- `eval(`
- `exec(`
- `__import__`

**Check:** Fail if forbidden strings found.

### Rule 6: Tool Deny Takes Precedence
If a tool is in both `tools.allow` and `tools.deny`, it MUST be treated as denied.

**Check:** Warn about contradictory entries.

### Rule 7: Version Format
`version` must follow semantic versioning: `MAJOR.MINOR.PATCH`

**Check:** Regex validation: `^\d+\.\d+\.\d+$`

### Rule 8: Name Format
`name` must be lowercase with only alphanumeric, underscore, and hyphen.

**Check:** Regex validation: `^[a-z][a-z0-9_-]*$`

## Severity Levels

| Severity | Action |
|----------|--------|
| ERROR | CI fails, must fix before merge |
| WARN | CI passes with warning, should fix |
| INFO | Informational, no action required |

## Running the Linter

```bash
# Lint all skills
python scripts/myca_skill_lint.py

# Lint specific skill
python scripts/myca_skill_lint.py --skill file_editor

# Verbose output
python scripts/myca_skill_lint.py --verbose

# JSON output (for CI)
python scripts/myca_skill_lint.py --json
```

## Adding New Rules

1. Document the rule in this file
2. Implement in `scripts/myca_skill_lint.py`
3. Add test cases
4. Submit PR with rule + tests
