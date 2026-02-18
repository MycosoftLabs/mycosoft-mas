# Dev Agent Playbook

**Version:** 1.0.0  
**Date:** February 17, 2026

## Overview

Step-by-step procedures for Dev Agent operations focused on implementing code changes safely and effectively.

---

## Playbook 1: Implement Feature

### Trigger
Feature task assigned by Manager.

### Steps

1. **Understand Requirements**
   ```python
   task = get_assigned_task()
   requirements = task.requirements
   
   # Ask clarifying questions if needed
   if requirements.is_ambiguous:
       escalate_for_clarification(task)
       return
   ```

2. **Plan Implementation**
   ```yaml
   implementation_plan:
     files_to_create: ["<list>"]
     files_to_modify: ["<list>"]
     dependencies_needed: ["<list>"]
     tests_to_write: ["<list>"]
     estimated_changes: <line count>
   ```

3. **Verify Permissions**
   ```python
   for file in plan.all_files:
       if not is_allowed_path(file):
           escalate(f"Cannot modify {file} - outside allowed paths")
           return
   ```

4. **Implement Changes**
   ```python
   # Follow existing patterns
   existing_code = read_similar_code()
   
   # Write code
   for file in plan.files_to_create:
       create_file(file, content_following_patterns(existing_code))
   
   for file in plan.files_to_modify:
       modify_file(file, changes_following_patterns(existing_code))
   ```

5. **Write Tests**
   ```python
   # Unit tests for new functions
   for function in new_functions:
       write_unit_test(function)
   
   # Integration test if applicable
   if changes_involve_multiple_components:
       write_integration_test()
   ```

6. **Run Tests in Sandbox**
   ```python
   result = sandbox.run_tests(
       tests=plan.tests_to_write + related_tests,
       timeout_seconds=300
   )
   
   if not result.all_passed:
       fix_failing_tests()
   ```

7. **Submit PR**
   ```yaml
   pr:
     title: "feat(<scope>): <description>"
     body: |
       ## Summary
       <what this adds>
       
       ## Changes
       - <file changes>
       
       ## Testing
       - [x] Unit tests added
       - [x] All tests passing
       
       ## Checklist
       - [x] Follows code style
       - [x] No security issues
     files: ["<list>"]
   ```

---

## Playbook 2: Fix Bug

### Trigger
Bug fix task assigned.

### Steps

1. **Reproduce Bug**
   ```python
   # Get reproduction steps
   repro_steps = task.reproduction_steps
   
   # Attempt reproduction in sandbox
   result = sandbox.execute(repro_steps)
   
   if not result.shows_bug:
       request_more_info(task)
       return
   ```

2. **Locate Bug**
   ```python
   # Trace execution
   trace = sandbox.trace_execution(repro_steps)
   
   # Find failing point
   failing_point = analyze_trace(trace)
   
   # Identify root cause
   root_cause = identify_root_cause(failing_point)
   ```

3. **Plan Fix**
   ```yaml
   fix_plan:
     root_cause: "<description>"
     fix_approach: "<how to fix>"
     files_to_modify: ["<list>"]
     risk_assessment: "low|medium|high"
   ```

4. **Implement Fix**
   ```python
   # Minimal change
   change = generate_minimal_fix(root_cause)
   
   # Apply change
   apply_change(change)
   ```

5. **Verify Fix**
   ```python
   # Bug should not reproduce
   result = sandbox.execute(repro_steps)
   assert not result.shows_bug
   
   # Existing tests still pass
   test_result = sandbox.run_tests()
   assert test_result.all_passed
   ```

6. **Add Regression Test**
   ```python
   # Write test that catches this bug
   regression_test = write_regression_test(
       bug_id=task.bug_id,
       repro_steps=repro_steps,
       expected_behavior="<correct behavior>"
   )
   ```

7. **Submit PR**
   ```yaml
   pr:
     title: "fix(<scope>): <bug description>"
     body: |
       ## Bug
       <description of bug>
       
       ## Root Cause
       <why it happened>
       
       ## Fix
       <what was changed>
       
       ## Testing
       - [x] Bug no longer reproduces
       - [x] Regression test added
       - [x] All tests passing
   ```

---

## Playbook 3: Refactor Code

### Trigger
Refactoring task assigned.

### Steps

1. **Understand Scope**
   ```python
   # What needs refactoring
   scope = task.refactoring_scope
   
   # Why (readability, performance, maintainability)
   motivation = task.motivation
   ```

2. **Map Dependencies**
   ```python
   # Find all usages
   usages = find_all_usages(scope.target)
   
   # Identify impact
   impacted_files = [u.file for u in usages]
   ```

3. **Plan Refactoring**
   ```yaml
   refactor_plan:
     target: "<what to refactor>"
     motivation: "<why>"
     approach: "<how>"
     impacted_files: ["<list>"]
     breaking_changes: true|false
     migration_needed: true|false
   ```

4. **Create Tests First**
   ```python
   # Ensure behavior is captured before changing
   if not has_sufficient_tests(scope.target):
       write_characterization_tests(scope.target)
   
   # Run baseline
   baseline_tests = sandbox.run_tests()
   assert baseline_tests.all_passed
   ```

5. **Refactor Incrementally**
   ```python
   for step in refactor_plan.steps:
       # Make small change
       apply_change(step)
       
       # Verify tests still pass
       result = sandbox.run_tests()
       if not result.all_passed:
           rollback(step)
           analyze_failure(result)
   ```

6. **Verify Behavior Unchanged**
   ```python
   # All original tests pass
   final_tests = sandbox.run_tests()
   assert final_tests.all_passed
   
   # No regressions
   assert final_tests.results == baseline_tests.results
   ```

7. **Submit PR**
   ```yaml
   pr:
     title: "refactor(<scope>): <description>"
     body: |
       ## Motivation
       <why refactoring>
       
       ## Changes
       <what changed>
       
       ## Behavior
       - [x] No behavior changes
       - [x] All tests passing
       - [x] Performance unchanged
   ```

---

## Playbook 4: Add Tests

### Trigger
Test coverage task assigned.

### Steps

1. **Identify Coverage Gaps**
   ```python
   # Get current coverage
   coverage = sandbox.run_coverage()
   
   # Find untested code
   gaps = coverage.get_uncovered_lines()
   ```

2. **Prioritize Tests**
   ```yaml
   test_priority:
     critical_paths: ["<list>"]  # Test first
     edge_cases: ["<list>"]
     error_handling: ["<list>"]
     happy_paths: ["<list>"]
   ```

3. **Write Unit Tests**
   ```python
   for gap in prioritized_gaps:
       # Understand the code
       code = read_code(gap.file, gap.lines)
       
       # Write test
       test = write_test(
           target=gap,
           test_type="unit",
           coverage_goal=["normal", "edge", "error"]
       )
       
       # Verify test works
       result = sandbox.run_test(test)
       assert result.passed
   ```

4. **Verify Coverage Improvement**
   ```python
   new_coverage = sandbox.run_coverage()
   
   improvement = new_coverage.percentage - coverage.percentage
   print(f"Coverage improved by {improvement}%")
   ```

5. **Submit PR**
   ```yaml
   pr:
     title: "test(<scope>): add tests for <area>"
     body: |
       ## Coverage
       Before: X%
       After: Y%
       
       ## Tests Added
       - <test list>
   ```

---

## Playbook 5: Update Documentation

### Trigger
Documentation task assigned.

### Steps

1. **Identify What Needs Docs**
   ```python
   # New code without docs
   undocumented = find_undocumented_code()
   
   # Outdated docs
   outdated = find_stale_docs()
   ```

2. **Write Documentation**
   ```python
   # Docstrings for functions
   for func in undocumented.functions:
       add_docstring(func)
   
   # README updates
   if undocumented.modules:
       update_readme(undocumented.modules)
   
   # API docs
   if undocumented.endpoints:
       update_api_docs(undocumented.endpoints)
   ```

3. **Verify Accuracy**
   ```python
   # Docs match code
   for doc in written_docs:
       verify_doc_matches_code(doc)
   ```

4. **Submit PR**
   ```yaml
   pr:
     title: "docs(<scope>): <description>"
     body: |
       ## Documentation Updates
       - <list of updates>
   ```

---

## Quick Reference

### Code Style
```python
# Type hints required
def function_name(arg1: str, arg2: int) -> dict:
    """
    Brief description.
    
    Args:
        arg1: Description.
        arg2: Description.
    
    Returns:
        Description of return value.
    """
    pass
```

### Test Pattern
```python
def test_function_does_x():
    # Arrange
    input_data = create_input()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected
```

### Safety Checklist
- [ ] No hardcoded secrets
- [ ] No eval/exec
- [ ] Error handling present
- [ ] Logging for important actions
- [ ] Tests for new code
- [ ] Within allowed paths
