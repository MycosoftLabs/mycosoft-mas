# MYCA Router Policy

**Version:** 1.0.0  
**Date:** February 17, 2026

## Overview

The Router Policy defines how tool calls are validated and routed through the MYCA permission enforcement system. This is the critical enforcement point that ensures agents cannot exceed their granted permissions.

## Architecture

```
Agent Request → Router → Permission Check → Tool Execution → Event Logging
                  ↓
            Skill Registry
                  ↓
         PERMISSIONS.json
```

## Enforcement Points

### 1. Pre-Execution Validation

Every tool call MUST pass through permission validation before execution:

```python
async def validate_tool_call(
    skill_name: str,
    tool_name: str,
    args: dict
) -> ValidationResult:
    """
    Validate a tool call against skill permissions.
    
    This is the primary enforcement point - called BEFORE any tool
    executes.
    """
    # Load skill permissions
    permissions = skill_registry.get_permissions(skill_name)
    if not permissions:
        return ValidationResult(
            allowed=False,
            reason="no_permissions_defined",
            risk_flag=True
        )
    
    # Check tool allowlist/denylist
    if not is_tool_allowed(tool_name, permissions):
        return ValidationResult(
            allowed=False,
            reason="tool_denied",
            tool=tool_name
        )
    
    # Check filesystem paths (if applicable)
    if has_filesystem_args(args):
        path_check = validate_paths(args, permissions.filesystem)
        if not path_check.allowed:
            return path_check
    
    # Check network access (if applicable)
    if has_network_args(args):
        network_check = validate_network(args, permissions.network)
        if not network_check.allowed:
            return network_check
    
    # Check secrets access (if applicable)
    if requests_secret(args):
        secret_check = validate_secret_access(args, permissions.secrets)
        if not secret_check.allowed:
            return secret_check
    
    return ValidationResult(allowed=True)
```

### 2. Tool Allow/Deny Lists

```python
def is_tool_allowed(tool_name: str, permissions: SkillPermissions) -> bool:
    """
    Check if a tool is allowed for this skill.
    
    Rules:
    1. If tool is in deny list, ALWAYS reject
    2. If allow list exists and tool not in it, reject
    3. Otherwise, allow
    
    Deny takes precedence over allow.
    """
    tools_config = permissions.tools
    
    # Deny list takes absolute precedence
    if tool_name in tools_config.get("deny", []):
        return False
    
    # If allow list exists, tool must be in it
    allow_list = tools_config.get("allow")
    if allow_list is not None:
        return tool_name in allow_list
    
    # No explicit lists = default allow
    return True
```

### 3. Filesystem Path Validation

```python
def validate_paths(args: dict, fs_config: dict) -> ValidationResult:
    """
    Validate filesystem paths against allow/deny patterns.
    
    Uses glob patterns (fnmatch) for matching.
    Deny patterns are checked first.
    """
    paths = extract_paths(args)
    allow_patterns = fs_config.get("allow", [])
    deny_patterns = fs_config.get("deny", [])
    
    for path in paths:
        # Normalize path
        normalized = normalize_path(path)
        
        # Check deny patterns first (these always win)
        for deny in deny_patterns:
            if fnmatch(normalized, deny):
                return ValidationResult(
                    allowed=False,
                    reason="path_denied",
                    path=path,
                    pattern=deny
                )
        
        # Check allow patterns
        allowed = False
        for allow in allow_patterns:
            if fnmatch(normalized, allow):
                allowed = True
                break
        
        if not allowed:
            return ValidationResult(
                allowed=False,
                reason="path_not_allowed",
                path=path
            )
    
    return ValidationResult(allowed=True)
```

### 4. Network Access Validation

```python
def validate_network(args: dict, net_config: dict) -> ValidationResult:
    """
    Validate network access against allowlist.
    
    If network is disabled, always reject.
    If enabled, URL must match an allowlist pattern.
    """
    if not net_config.get("enabled", False):
        return ValidationResult(
            allowed=False,
            reason="network_disabled"
        )
    
    urls = extract_urls(args)
    allowlist = net_config.get("allowlist", [])
    
    for url in urls:
        domain = extract_domain(url)
        
        allowed = False
        for pattern in allowlist:
            if domain_matches(domain, pattern):
                allowed = True
                break
        
        if not allowed:
            return ValidationResult(
                allowed=False,
                reason="domain_not_allowed",
                domain=domain
            )
    
    return ValidationResult(allowed=True)
```

### 5. Secrets Access Validation

```python
def validate_secret_access(args: dict, secrets_config: dict) -> ValidationResult:
    """
    Validate secret access against allowed scopes.
    
    Secrets are NEVER returned to agents directly.
    Instead, validated access is passed to the tool for internal use.
    """
    requested_scopes = extract_secret_scopes(args)
    allowed_scopes = secrets_config.get("allowed_scopes", [])
    
    for scope in requested_scopes:
        if scope not in allowed_scopes:
            return ValidationResult(
                allowed=False,
                reason="secret_scope_denied",
                scope=scope
            )
    
    # Even if allowed, log the access attempt
    event_ledger.log_secret_access(
        skill=current_skill(),
        scopes=requested_scopes,
        allowed=True
    )
    
    return ValidationResult(allowed=True)
```

## Event Logging

All tool calls are logged to the Event Ledger:

```python
async def log_tool_event(
    skill_name: str,
    tool_name: str,
    args: dict,
    result: Any,
    validation: ValidationResult,
    duration_ms: int
):
    """Log tool call to Event Ledger for audit trail."""
    event = {
        "ts": datetime.utcnow().isoformat(),
        "skill": skill_name,
        "tool": tool_name,
        "args_hash": hash_args(args),  # Privacy: hash, don't log raw
        "allowed": validation.allowed,
        "reason": validation.reason if not validation.allowed else None,
        "duration_ms": duration_ms,
        "risk_flag": getattr(validation, "risk_flag", False),
    }
    
    await event_ledger.append(event)
```

## Sandbox Enforcement

High-risk operations require sandbox execution:

```python
async def execute_with_sandbox_check(
    skill_name: str,
    tool_name: str,
    executor: Callable
) -> Any:
    """
    Check if sandbox is required and enforce it.
    """
    permissions = skill_registry.get_permissions(skill_name)
    
    if permissions.limits.get("sandbox_required", False):
        # Must execute in sandbox
        return await sandbox.execute(executor)
    
    # Check if tool itself requires sandbox
    tool_info = get_tool_info(tool_name)
    if tool_info.get("requires_sandbox", False):
        return await sandbox.execute(executor)
    
    # Direct execution allowed
    return await executor()
```

## Rate Limiting

```python
async def check_rate_limits(
    skill_name: str,
    tool_name: str
) -> bool:
    """
    Enforce rate limits from permissions.
    """
    permissions = skill_registry.get_permissions(skill_name)
    limits = permissions.get("limits", {})
    
    # Per-minute limit
    per_minute = limits.get("max_calls_per_minute")
    if per_minute:
        recent = count_recent_calls(skill_name, tool_name, minutes=1)
        if recent >= per_minute:
            return False
    
    # Max concurrent
    max_concurrent = limits.get("max_concurrent")
    if max_concurrent:
        concurrent = count_concurrent_calls(skill_name)
        if concurrent >= max_concurrent:
            return False
    
    return True
```

## Error Handling

```python
class PermissionDeniedError(Exception):
    """Raised when a tool call violates permissions."""
    def __init__(self, reason: str, details: dict = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Permission denied: {reason}")


async def handle_permission_denied(
    skill_name: str,
    tool_name: str,
    validation: ValidationResult
):
    """Handle permission denial with proper logging and response."""
    # Log the denial
    await event_ledger.append({
        "ts": datetime.utcnow().isoformat(),
        "event_type": "permission_denied",
        "skill": skill_name,
        "tool": tool_name,
        "reason": validation.reason,
        "details": validation.to_dict(),
    })
    
    # If suspicious, flag for security review
    if validation.risk_flag:
        await security_queue.enqueue({
            "type": "suspicious_access",
            "skill": skill_name,
            "tool": tool_name,
            "reason": validation.reason,
        })
    
    # Raise exception (do not reveal internal details to agent)
    raise PermissionDeniedError(
        reason="access_denied",
        details={"tool": tool_name}  # Minimal info
    )
```

## Integration with Existing MAS

The router integrates with the existing MAS infrastructure:

1. **tool_pipeline.py** - `ToolExecutor.execute()` calls permission validation
2. **skill_registry.py** - `PermissionValidator` provides validation logic
3. **audit.py** - `AuditEventBridge` logs to both legacy audit and EventLedger
4. **sandboxing.py** - Existing sandbox infrastructure handles high-risk execution

## Non-Negotiables

1. **Every tool call passes through validation** - No exceptions
2. **Deny always wins** - No allow can override a deny
3. **All calls are logged** - Complete audit trail
4. **Secrets are never returned to agents** - Only passed to tools internally
5. **Sandbox required for high-risk** - No bypassing
6. **Rate limits are enforced** - Protection against abuse

## See Also

- [SYSTEM_CONSTITUTION.md](constitution/SYSTEM_CONSTITUTION.md)
- [TOOL_USE_RULES.md](constitution/TOOL_USE_RULES.md)
- [PERMISSIONS.schema.json](skill_permissions/_schema/PERMISSIONS.schema.json)
- [Event Ledger](event_ledger/README.md)
