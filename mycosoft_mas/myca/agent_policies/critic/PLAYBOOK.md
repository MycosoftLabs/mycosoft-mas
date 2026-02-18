# Critic Agent Playbook

**Version:** 1.0.0  
**Date:** February 17, 2026

## Overview

Step-by-step procedures for Critic Agent operations focused on failure analysis and patch generation.

---

## Playbook 1: Analyze Test Failure

### Trigger
CI test failure reported.

### Steps

1. **Gather Failure Context**
   ```python
   failure_info = {
       "test_name": ci_result.failed_tests[0].name,
       "test_file": ci_result.failed_tests[0].file,
       "error_message": ci_result.failed_tests[0].error,
       "stack_trace": ci_result.failed_tests[0].trace,
       "pr_id": ci_result.pr_id,
       "changed_files": ci_result.changed_files,
   }
   ```

2. **Identify Failure Type**
   | Type | Indicators |
   |------|------------|
   | Assertion failure | `AssertionError` |
   | Type error | `TypeError`, `AttributeError` |
   | Import error | `ImportError`, `ModuleNotFoundError` |
   | Runtime error | `RuntimeError`, `ValueError` |
   | Timeout | `TimeoutError` |

3. **Trace Root Cause**
   ```python
   # Read the failing test
   test_code = read_file(failure_info["test_file"])
   
   # Find the specific line
   failing_line = extract_failing_line(failure_info["stack_trace"])
   
   # Identify changed code that caused failure
   changed_code = get_diff_for_files(failure_info["changed_files"])
   
   # Correlate
   root_cause = correlate_failure_with_changes(
       test_code, failing_line, changed_code
   )
   ```

4. **Generate Fix**
   ```python
   patch = generate_minimal_patch(
       root_cause=root_cause,
       constraints=[
           "minimal_change",
           "preserve_intent",
           "fix_test_without_weakening"
       ]
   )
   ```

5. **Verify Fix**
   ```python
   # Run test with patch applied (in sandbox)
   result = sandbox.run_tests(
       tests=[failure_info["test_name"]],
       with_patch=patch
   )
   assert result.passed
   ```

6. **Create Regression Test**
   ```yaml
   regression_test:
     id: "rt_<failure_id>"
     name: "Regression for <failure description>"
     input: "<reproduction input>"
     expected: "<correct behavior>"
   ```

---

## Playbook 2: Analyze Eval Failure

### Trigger
MYCA evaluation failure detected.

### Steps

1. **Load Eval Details**
   ```python
   eval_result = load_eval_result(eval_id)
   test_case = load_test_case(eval_result.test_id)
   ```

2. **Classify Eval Category**
   | Category | Analysis Focus |
   |----------|----------------|
   | prompt_injection | Check defense mechanisms |
   | secret_exfiltration | Check output filtering |
   | permission_boundary | Check enforcement code |
   | jailbreak | Check constitution adherence |

3. **Analyze Agent Behavior**
   ```python
   # Get agent's actual response
   actual_response = eval_result.agent_response
   
   # Compare to expected
   expected_behavior = test_case.expected_behavior
   
   # Identify violation
   violation = find_violation(actual_response, expected_behavior)
   ```

4. **Trace to Code**
   ```python
   # Find the code path that led to violation
   if violation.type == "tool_called_when_should_block":
       # Check permission enforcement
       check_permission_code()
   elif violation.type == "content_leaked":
       # Check output filtering
       check_output_filters()
   ```

5. **Generate Strengthening Patch**
   ```python
   patch = generate_defense_patch(
       violation_type=violation.type,
       code_location=violation.code_path,
       additional_checks=derive_new_checks(violation)
   )
   ```

6. **Add Adversarial Test**
   ```yaml
   # Add stronger test that catches this
   new_test:
     id: "adv_<category>_<seq>"
     name: "Strengthened test for <violation>"
     input_text: "<attack that exposed weakness>"
     expected_behavior: "block"
     severity: "high"
   ```

---

## Playbook 3: Generate Patch from Failure

### Trigger
Root cause identified, need patch.

### Steps

1. **Define Patch Constraints**
   ```yaml
   constraints:
     - Fix the specific issue only
     - Do not change unrelated code
     - Do not weaken existing defenses
     - Maintain backward compatibility
     - Include inline comments
   ```

2. **Generate Minimal Diff**
   ```python
   # Identify minimum change needed
   min_change = identify_minimum_change(root_cause)
   
   # Generate diff
   patch = Patch(
       file=min_change.file,
       changes=[
           Change(
               line_start=min_change.start,
               line_end=min_change.end,
               old_content=min_change.old,
               new_content=min_change.new,
           )
       ]
   )
   ```

3. **Validate Patch Quality**
   ```python
   validations = [
       ("syntactically_valid", check_syntax(patch)),
       ("passes_lint", check_lint(patch)),
       ("fixes_issue", run_test_with_patch(patch)),
       ("no_regressions", run_all_tests(patch)),
   ]
   assert all(v[1] for v in validations)
   ```

4. **Format Patch Submission**
   ```yaml
   submission:
     title: "fix(<scope>): <brief description>"
     body: |
       ## Root Cause
       <analysis>
       
       ## Fix
       <explanation>
       
       ## Testing
       - [x] Failing test now passes
       - [x] No new regressions
       - [x] Added regression test
       
       ## Regression Test
       <test_id>
     patch: "<diff>"
   ```

---

## Playbook 4: Create Regression Test

### Trigger
Patch created, need regression test.

### Steps

1. **Determine Test Category**
   | Failure Type | Test Category |
   |--------------|---------------|
   | Security violation | `adversarial/` |
   | Permission boundary | `golden_tasks/permission_boundary` |
   | Output leak | `golden_tasks/secret_exfiltration` |
   | Logic error | `golden_tasks/safe_operations` |

2. **Design Test Case**
   ```yaml
   test_case:
     # Must fail before patch
     precondition: "Test fails on main branch"
     
     # Must pass after patch
     postcondition: "Test passes with patch applied"
     
     # Test structure
     id: "rt_<failure_id>_001"
     name: "Regression: <failure description>"
     category: "<determined category>"
     severity: "high"  # Regressions are high severity
     
     input_text: |
       <exact input that triggered failure>
     
     expected_behavior: "block|allow"
     
     added_date: "2026-02-17"
     related_failure: "<original failure id>"
   ```

3. **Verify Test**
   ```python
   # Test fails without patch
   result_before = run_eval(test_case, without_patch=True)
   assert result_before.failed
   
   # Test passes with patch
   result_after = run_eval(test_case, with_patch=True)
   assert result_after.passed
   ```

4. **Add to Test Suite**
   ```python
   add_test_to_suite(
       category=test_case.category,
       test=test_case,
       related_patch=patch_id
   )
   ```

---

## Playbook 5: Pattern Analysis

### Trigger
Multiple related failures detected.

### Steps

1. **Gather Related Failures**
   ```python
   failures = event_ledger.query_failures(
       time_range="7d",
       min_count=3
   )
   
   # Group by pattern
   patterns = cluster_failures_by_pattern(failures)
   ```

2. **Analyze Pattern**
   ```yaml
   pattern_analysis:
     pattern_id: "pat_<hash>"
     occurrences: <count>
     common_factors:
       - agent_type: "<type>"
       - tool: "<tool>"
       - error_category: "<category>"
     hypothesis: "<what's causing repeated failures>"
   ```

3. **Propose Systemic Fix**
   ```yaml
   systemic_fix:
     type: "policy|code|test"
     description: "<what needs to change>"
     impact: "<files or policies affected>"
     risk: "low|medium|high"
   ```

4. **Submit for Review**
   ```python
   improvement_queue.submit(
       type="systemic_improvement",
       analysis=pattern_analysis,
       proposed_fix=systemic_fix,
       priority="high"
   )
   ```

---

## Quick Reference

### Failure Categories
| Code | Category | Action |
|------|----------|--------|
| `F001` | Test assertion | Analyze test logic |
| `F002` | Import error | Check dependencies |
| `F003` | Type error | Check type annotations |
| `F004` | Security eval | Analyze defense gap |
| `F005` | Timeout | Check complexity |

### Patch Quality Checklist
- [ ] Fixes the specific issue
- [ ] Minimal change
- [ ] Syntactically valid
- [ ] Passes lint
- [ ] Includes regression test
- [ ] Clear commit message
- [ ] No security weakening
