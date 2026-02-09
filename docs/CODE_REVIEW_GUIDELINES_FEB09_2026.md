# Code Review Guidelines

**Date:** February 9, 2026
**Applies to:** All Mycosoft repositories (MAS, Website, MINDEX, MycoBrain, NatureOS, Mycorrhizae, NLM, SDK, platform-infra)

---

## Purpose

Code review is a mandatory quality gate for all changes entering `main`. It catches bugs, security issues, and design problems before they reach production. Every engineer (including MYCA autonomous agent) must submit changes via PR and receive approval before merging.

---

## Review SLA

| Change Size | Response Time | Approval Time |
|------------|---------------|---------------|
| Small (< 50 lines, docs, config) | Within 12 hours | Within 24 hours |
| Medium (50-300 lines, single feature) | Within 24 hours | Within 48 hours |
| Large (300+ lines, multi-system) | Within 24 hours | Within 72 hours |
| Hotfix (production incident) | Within 4 hours | Within 8 hours |

**If you cannot review within the SLA, reassign or notify the author.**

---

## Approval Requirements

| Change Type | Minimum Reviewers | Who Can Approve |
|------------|-------------------|-----------------|
| Documentation only | 1 | Any team member |
| Bug fix | 1 | Any team member |
| New feature | 1 | Any team member |
| New agent or API endpoint | 1 | Backend lead or any senior |
| Security changes (`security/`, `safety/`, auth) | 2 | Security-aware reviewer required |
| Architecture changes (orchestrator, core) | 2 | Tech lead or CTO required |
| Protected files (see CLAUDE.md) | 2 + CEO approval | CTO + CEO |
| Database migrations | 2 | Database engineer required |
| CI/CD pipeline changes | 1 | DevOps engineer |

---

## Review Checklist

Every reviewer must check each category. Use this checklist in your review comments.

### 1. Correctness

- [ ] Code does what the PR description says it does
- [ ] Edge cases are handled (null, empty, timeout, error states)
- [ ] No off-by-one errors, race conditions, or deadlocks
- [ ] Async/await used correctly (no missing awaits, no unhandled promises)
- [ ] Error handling is present and meaningful (not swallowed silently)
- [ ] Return types match expected behavior

### 2. Security

- [ ] **No hardcoded secrets, API keys, tokens, or passwords** in code or config
- [ ] Secrets loaded from environment variables or secret management
- [ ] Input validation on all user-facing endpoints (query params, body, headers)
- [ ] No SQL injection vectors (use parameterized queries, ORM methods)
- [ ] No command injection (no `os.system()`, `subprocess` with shell=True on user input)
- [ ] Authentication and authorization checks present on new endpoints
- [ ] Rate limiting considered for public-facing endpoints
- [ ] No sensitive data in logs (mask PII, tokens, passwords)
- [ ] CORS settings are restrictive (not `*` in production)
- [ ] File uploads validated (type, size, content)

### 3. Performance

- [ ] No N+1 query patterns (batch database calls)
- [ ] Large datasets paginated (not loading everything into memory)
- [ ] Expensive operations cached where appropriate
- [ ] No unnecessary re-renders in React components (check deps arrays)
- [ ] Images optimized (WebP, lazy loading, proper sizing)
- [ ] No blocking operations on the main thread
- [ ] Database queries use proper indexes
- [ ] WebSocket/SSE connections cleaned up on unmount

### 4. Readability

- [ ] Code follows existing patterns in the codebase
- [ ] Variable and function names are descriptive (`isLoading`, `hasError`, not `x`, `tmp`)
- [ ] No commented-out code blocks (delete or explain why kept)
- [ ] Complex logic has inline comments explaining *why* (not *what*)
- [ ] Functions are reasonably sized (< 50 lines preferred)
- [ ] No deeply nested conditionals (flatten with early returns)
- [ ] Consistent formatting (run linter before submitting)

### 5. Typing

- [ ] TypeScript: strict types, no `any` without justification
- [ ] Python: type hints on function signatures, Pydantic models for API
- [ ] C#: proper nullable annotations
- [ ] Interfaces preferred over type aliases (TypeScript)
- [ ] Enums avoided in TypeScript (use maps/objects instead)
- [ ] Generic types used where reusability is needed

### 6. Testing

- [ ] **New features have tests** (unit, integration, or E2E as appropriate)
- [ ] **Bug fixes include a regression test** that would have caught the bug
- [ ] Tests cover happy path AND error/edge cases
- [ ] Tests are deterministic (no flaky tests, no time-dependent assertions)
- [ ] Mocks are minimal and justified (prefer real implementations)
- [ ] Test names describe the scenario: `test_memory_api_returns_404_for_missing_id`
- [ ] No `console.log` or `print()` left in test code

### 7. Documentation

- [ ] PR description explains *what* changed and *why*
- [ ] New agents registered in `docs/SYSTEM_REGISTRY_FEB04_2026.md`
- [ ] New API endpoints added to `docs/API_CATALOG_FEB04_2026.md`
- [ ] New docs indexed in `docs/MASTER_DOCUMENT_INDEX.md`
- [ ] README or inline docs updated if public interface changed
- [ ] Breaking changes documented with migration instructions
- [ ] Config changes documented (new env vars, new dependencies)

---

## Language-Specific Standards

### Python (MAS, MINDEX, Mycorrhizae)

```python
# Formatting
black --check mycosoft_mas/
isort --check mycosoft_mas/

# Type checking
mypy mycosoft_mas/ --ignore-missing-imports

# Tests
poetry run pytest tests/ -v --tb=short
```

- Follow PEP 8 (enforced by Black)
- Type hints on all public functions
- Pydantic models for request/response schemas
- BaseAgent pattern for new agents (see CLAUDE.md)
- Docstrings on public classes and functions

### TypeScript (Website)

```bash
# Lint
npm run lint

# Type check
npx tsc --noEmit

# Unit tests
npm test

# E2E tests
npx playwright test
```

- Strict TypeScript (`strict: true` in tsconfig)
- Functional components with interfaces
- Server Components by default, minimize `use client`
- Shadcn UI + Radix + Tailwind for styling
- No `any` type without a comment explaining why

### C++ (MycoBrain firmware)

- PlatformIO build must pass
- Memory-safe patterns (no raw `malloc` without `free`)
- Serial protocol changes must be backward-compatible
- Test on hardware before merging firmware changes

### C# (NatureOS)

- Follow .NET conventions
- `dotnet build` must pass with no warnings
- Nullable reference types enabled
- Controller actions must have proper authorization attributes

---

## Automated Checks (Must Pass Before Merge)

These run automatically on every PR via GitHub Actions:

| Check | MAS | Website | MINDEX |
|-------|-----|---------|--------|
| Lint | black, isort, flake8 | ESLint | black, isort |
| Type check | mypy | tsc --noEmit | mypy |
| Unit tests | pytest | jest | pytest |
| Build | Docker build | next build | Docker build |
| E2E tests | -- | Playwright | -- |
| Security scan | bandit | npm audit | bandit |

**All checks must be green before the PR can be merged.**

---

## How to Review

### For Reviewers

1. **Read the PR description first** -- Understand the intent before reading code
2. **Pull the branch locally** if the change is complex -- run it, test it
3. **Check the diff against the checklist** above, category by category
4. **Leave specific, actionable comments** -- "This query might be slow because X. Consider adding an index on Y." Not just "This is slow."
5. **Approve or Request Changes** -- Don't leave reviews in a "Comment" limbo state
6. **Use suggestions** for small fixes (GitHub inline suggestion feature)
7. **If you approve with minor nits**, say "Approve with nits" and list them -- don't block the PR

### For Authors

1. **Self-review before requesting review** -- Read your own diff first
2. **Keep PRs small** -- < 300 lines preferred. Split large features into stacked PRs
3. **Write a clear PR description** -- What changed, why, how to test
4. **Respond to all comments** -- Resolve or explain why you disagree
5. **Don't merge your own PR** without at least 1 approval (except emergency hotfixes with post-merge review)
6. **Run CI locally before pushing** to avoid wasting reviewer time on obvious failures

---

## Common Review Anti-Patterns (Avoid These)

| Anti-Pattern | Why It's Bad | What to Do Instead |
|-------------|-------------|-------------------|
| Rubber-stamp approval | Misses bugs and security issues | Actually read the code, check the checklist |
| Nitpicking style only | Wastes time on formatting robots handle | Focus on logic, security, architecture |
| Blocking on opinion | Stalls velocity on subjective preferences | Suggest, don't block. Accept reasonable alternatives |
| Drive-by comments without resolution | Creates confusion | Always approve or request changes |
| Reviewing 1000+ line PRs | Can't catch anything in a wall of code | Ask the author to split the PR |
| Ignoring test coverage | Bugs ship without safety nets | Require tests for new features and bug fixes |

---

## Registry Update Reminders

After merging PRs that add or change these, update the corresponding registries:

| Change | Registry to Update |
|--------|-------------------|
| New agent | `docs/SYSTEM_REGISTRY_FEB04_2026.md`, `mycosoft_mas/agents/__init__.py` |
| New API endpoint | `docs/API_CATALOG_FEB04_2026.md`, register in `myca_main.py` |
| New service | `docs/SYSTEM_REGISTRY_FEB04_2026.md` |
| New device | `docs/SYSTEM_REGISTRY_FEB04_2026.md` |
| New documentation | `docs/MASTER_DOCUMENT_INDEX.md` |
| New website page | Website sitemap, verify in browser |
| New env variable | `.env` template, deployment docs |

---

## Summary

| Rule | Policy |
|------|--------|
| PR required | Yes, for all changes to `main` |
| Self-merge | Prohibited (except emergency hotfix with post-merge review) |
| Review SLA | 24 hours for standard, 4 hours for hotfix |
| Minimum reviewers | 1 standard, 2 for security/architecture |
| CI must pass | Mandatory before merge |
| Tests required | Yes, for new features and bug fixes |
| Registry updates | Mandatory when adding agents, APIs, services, docs |
| No hardcoded secrets | Zero tolerance -- immediate request for changes |
