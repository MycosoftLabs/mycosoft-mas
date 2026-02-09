#!/bin/bash
# PreToolUse hook: Block destructive commands in Claude Code sessions
# Exit 0 = allow, Exit 2 = block

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [ -z "$CMD" ]; then
    exit 0
fi

# Block destructive commands
if echo "$CMD" | grep -iE '\b(rm\s+-rf\s+/|rm\s+-rf\s+\*|DROP\s+TABLE|DROP\s+DATABASE|DELETE\s+FROM|TRUNCATE\s+TABLE)\b' > /dev/null 2>&1; then
    echo "BLOCKED: Destructive command detected. This requires explicit approval." >&2
    exit 2
fi

# Block modifying protected files
PROTECTED_FILES="orchestrator\.py|orchestrator_service\.py|guardian_agent\.py|sandboxing\.py"
if echo "$CMD" | grep -E "(edit|write|rm|mv|sed|awk).*($PROTECTED_FILES)" > /dev/null 2>&1; then
    echo "BLOCKED: Cannot modify protected system files (orchestrator, guardian, sandboxing)." >&2
    exit 2
fi

# Block systemctl operations
if echo "$CMD" | grep -iE '\bsystemctl\s+(stop|disable|mask)\b' > /dev/null 2>&1; then
    echo "BLOCKED: Cannot stop/disable system services." >&2
    exit 2
fi

exit 0
