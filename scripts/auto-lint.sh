#!/bin/bash
# PostToolUse hook: Auto-lint after file changes
# Runs silently, exit 0 always (lint failures shouldn't block)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"

# Only lint if poetry is available and we're in the MAS repo
if command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
    poetry run black --check --quiet mycosoft_mas/ 2>/dev/null || true
    poetry run isort --check --quiet mycosoft_mas/ 2>/dev/null || true
fi

exit 0
