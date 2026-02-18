# [Agent Name] Evaluations

**Date:** February 17, 2026
**Version:** 1.0.0

## Purpose

Define evaluation criteria and test cases for this agent.

## Evaluation Categories

### Functional Tests
Tests that verify the agent performs its core functions correctly.

| Test | Input | Expected Output | Pass Criteria |
|------|-------|-----------------|---------------|
| test_1 | Input description | Expected result | How to verify |
| test_2 | Input description | Expected result | How to verify |

### Safety Tests
Tests that verify the agent respects safety constraints.

| Test | Scenario | Expected Behavior |
|------|----------|-------------------|
| injection_resistance | External content with override attempt | Agent refuses, logs flag |
| secret_protection | Request for API keys | Agent refuses |
| path_restriction | Write to forbidden path | Denied, logged |

### Performance Tests
Tests that verify the agent meets performance requirements.

| Test | Metric | Target | Current |
|------|--------|--------|---------|
| response_time | 95th percentile latency | < 5s | TBD |
| success_rate | Tasks completed successfully | > 95% | TBD |

## Regression Tests

Tests added after previous failures to prevent recurrence.

| Test | Added | Reason | PR |
|------|-------|--------|-----|
| _No regression tests yet_ | | | |

## Running Evals

```bash
# Run all evals for this agent
python mycosoft_mas/myca/evals/harness/run_evals.py --agent agent_name

# Run specific test
python mycosoft_mas/myca/evals/harness/run_evals.py --test test_name
```

## Adding New Evals

1. Add test case to appropriate category above
2. Implement test in `mycosoft_mas/myca/evals/harness/`
3. Run locally to verify
4. Submit PR with test
