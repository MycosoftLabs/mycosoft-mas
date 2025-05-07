#!/bin/bash

# Exit on error
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
for cmd in poetry pip pipdeptree; do
    if ! command_exists "$cmd"; then
        echo "Error: $cmd is required but not installed."
        exit 1
    fi
done

# Update Poetry
echo "Updating Poetry..."
poetry self update

# Update dependencies
echo "Updating dependencies..."
poetry update

# Check for conflicts
echo "Checking for dependency conflicts..."
pipdeptree --warn fail

# Generate requirements.txt for Docker
echo "Generating requirements.txt..."
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Generate SBOM
echo "Generating Software Bill of Materials..."
poetry export -f requirements.txt --output sbom.txt --with-hashes

# Check for security vulnerabilities
echo "Checking for security vulnerabilities..."
pip-audit

# Update lock file
echo "Updating lock file..."
poetry lock --no-update

echo "Dependency update completed successfully!" 