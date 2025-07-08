#!/bin/bash
# Setup script for Mycosoft MAS in Codex environment
# Installs Python and Node dependencies using local files
set -e

# Create Python virtual environment if not present
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Install project in editable mode
pip install -e .

# Install Node.js dependencies if package.json exists
if [ -f package.json ]; then
    npm install --legacy-peer-deps
fi

echo "Setup complete. Activate the virtual environment with 'source venv/bin/activate'."

