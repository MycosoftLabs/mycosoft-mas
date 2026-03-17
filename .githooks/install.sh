#!/usr/bin/env bash
# =============================================================================
# Install git hooks from .githooks/ directory
# Usage: bash .githooks/install.sh
# =============================================================================
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: Not inside a git repository."
    exit 1
fi

HOOKS_DIR="$REPO_ROOT/.githooks"

echo "Configuring git to use $HOOKS_DIR for hooks..."
git config core.hooksPath "$HOOKS_DIR"

# Ensure hooks are executable
chmod +x "$HOOKS_DIR/pre-commit" 2>/dev/null || true

echo "Done. Git hooks installed from .githooks/"
echo "  Pre-commit hook will block commits containing hardcoded secrets."
echo "  To bypass (not recommended): git commit --no-verify"
