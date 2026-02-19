# Auto-Apply Analyzer Fixes – Feb 09, 2026

How to make fixes from the analyzer (linter, code-auditor, Cursor) apply automatically once you approve them.

---

## 1. Linter Auto-Fix on Save (Cursor/VSCode)

### ESLint (Website, TypeScript)

Add to your Cursor/VSCode **User** or **Workspace** `settings.json`:

```json
{
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "always"
  }
}
```

- **Effect**: Every time you save a `.ts`/`.tsx`/`.js` file, ESLint auto-fixable issues are applied.
- **Scope**: All ESLint rules that support `--fix`.
- **Location**: `File > Preferences > Settings` (Ctrl+,) → search `codeActionsOnSave` → "Edit in settings.json", or add to `.vscode/settings.json` in the workspace.

### Python (Black, isort, Ruff)

Cursor uses Pylance for diagnostics. For **formatting** (Black, isort), use format-on-save:

```json
{
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

For **Ruff auto-fix** (imports, unused vars, etc.):

```json
{
  "editor.codeActionsOnSave": {
    "source.fixAll": "explicit",
    "source.organizeImports.ruff": "explicit"
  }
}
```

*(Requires Ruff extension: `charliermarsh.ruff`.)*

---

## 2. Bulk Fix via Terminal (One-Shot)

Use these when you want to fix everything in one run instead of on save.

### Website (ESLint)

```bash
cd WEBSITE/website
npm run lint -- --fix
```

### MAS (Python)

```bash
cd MAS/mycosoft-mas
make fmt
# or:
poetry run black mycosoft_mas/ tests/
poetry run isort mycosoft_mas/ tests/
```

If using Ruff for lint+fix:

```bash
poetry run ruff check mycosoft_mas/ tests/ --fix
poetry run ruff format mycosoft_mas/ tests/
```

---

## 3. Cursor "Auto-Fix Lints" (Built-In)

Cursor has an **Auto-Fix Lints** option that targets Error-level problems.

- **Where**: Cursor Settings → search "auto fix" or "linter".
- **Behavior**: When the agent/Composer makes edits, it can try to fix linter errors automatically.
- **Tip**: Enable it so the agent applies fixes as it writes code.

---

## 4. Code-Auditor Findings → Apply via Agent

The **code-auditor** produces reports (TODOs, FIXMEs, stubs, etc.); it does not edit files. To get those fixes applied:

1. **Run the gap scan**:
   ```bash
   python scripts/gap_scan_cursor_background.py
   ```

2. **Read the report**: `.cursor/gap_report_latest.json` and `gap_report_index.json`.

3. **Invoke an agent to apply fixes**:
   - In Cursor Chat: `@stub-implementer` or `@bug-fixer`
   - Say: *"Apply fixes for all approved items from the gap report. Focus on: [list patterns, e.g. hardcoded paths, missing validation, mock data]."*

4. **Approve in chat**: The agent will propose edits. You can say *"Apply all"* or accept each change. In Composer, use **Ctrl+Enter** to accept a diff, **Ctrl+Backspace** to reject.

### Batch-Apply Pattern

- Paste the gap report (or a subset) into the chat.
- Add: *"I approve all these fixes. Apply them."*
- The agent will make the edits; you approve the resulting diffs.

---

## 5. Pre-Commit Hook (Auto-Fix Before Commit)

To run formatters/linters before every commit:

```bash
# MAS repo
cd MAS/mycosoft-mas
pip install pre-commit
# Create .pre-commit-config.yaml with black, isort, ruff, eslint
pre-commit install
```

Example `.pre-commit-config.yaml` (MAS):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        args: [--config=pyproject.toml]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: [--profile=black]
```

---

## Summary

| Analyzer           | Auto-apply method                         |
|--------------------|-------------------------------------------|
| ESLint             | `editor.codeActionsOnSave` + `source.fixAll.eslint` |
| Black/isort        | `editor.formatOnSave` + Black formatter   |
| Ruff               | Ruff extension + `codeActionsOnSave`      |
| Code-auditor       | Run scan → hand report to @stub-implementer / @bug-fixer |
| Cursor built-in    | Enable "Auto-Fix Lints" in Cursor settings |

---

## References

- `format-and-lint` skill – CLI commands for fmt/lint
- `code-auditor` agent – gap scan, TODOs, FIXMEs
- `stub-implementer` agent – replaces placeholders with real code
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`
