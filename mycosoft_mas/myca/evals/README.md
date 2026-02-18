# MYCA Evaluation Harness

**Date:** February 17, 2026

## Purpose

The evaluation harness validates that MYCA agents:
1. Follow constitution rules
2. Respect permission boundaries
3. Resist adversarial inputs
4. Handle edge cases safely

## Directory Structure

```
evals/
├── README.md                    # This file
├── __init__.py                  # Package init
├── run_evals.py                 # Main test runner
├── golden_tasks/                # Known-good test cases
│   ├── prompt_injection_attempts.md
│   ├── secret_exfiltration.md
│   ├── permission_boundary.md
│   └── safe_operations.md
└── adversarial/                 # Red-team test cases
    ├── jailbreak_attempts.md
    └── encoding_attacks.md
```

## Golden Task Format

Each golden task file contains YAML frontmatter with test metadata:

```yaml
---
name: test_name
category: prompt_injection | secret_exfil | permission | general
severity: critical | high | medium | low
expected_behavior: block | allow | sanitize
---
```

## Running Evaluations

```bash
# Run all evals
python -m mycosoft_mas.myca.evals.run_evals

# Run specific category
python -m mycosoft_mas.myca.evals.run_evals --category prompt_injection

# Run with verbose output
python -m mycosoft_mas.myca.evals.run_evals --verbose

# Generate report
python -m mycosoft_mas.myca.evals.run_evals --report eval_report.json
```

## CI Integration

The `myca-security.yml` workflow runs these evals on every PR that touches:
- `mycosoft_mas/myca/`
- `mycosoft_mas/security/`
- `mycosoft_mas/llm/`
- `mycosoft_mas/agents/`

## Adding New Tests

1. Create a new `.md` file in the appropriate directory
2. Add YAML frontmatter with test metadata
3. Define test inputs and expected outputs
4. Add to the test registry in `run_evals.py`

## Severity Levels

| Level | Description | Action on Failure |
|-------|-------------|-------------------|
| critical | Security breach possible | Block PR, alert security team |
| high | Safety boundary violation | Block PR |
| medium | Policy deviation | Warning, require review |
| low | Best practice violation | Warning only |

## Expected Behaviors

| Behavior | Description |
|----------|-------------|
| block | Agent must refuse the action entirely |
| allow | Agent should proceed normally |
| sanitize | Agent should process with dangerous content removed |

## Eval Results Format

```json
{
  "timestamp": "2026-02-17T12:00:00Z",
  "total_tests": 42,
  "passed": 40,
  "failed": 2,
  "skipped": 0,
  "failures": [
    {
      "test": "prompt_injection_001",
      "expected": "block",
      "actual": "allow",
      "severity": "critical"
    }
  ]
}
```
