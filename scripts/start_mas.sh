#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export PYTHONPATH=$(pwd)
export MAS_ENV=development

# Start the MAS
python -m mycosoft_mas.run_mas 