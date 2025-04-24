# Setup script for Mycosoft MAS test environment
Write-Host "Setting up Mycosoft MAS test environment..."

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Python is installed: $pythonVersion"
} catch {
    Write-Host "Error: Python is not installed. Please install Python 3.11 or later."
    exit 1
}

# Check if Poetry is installed
try {
    $poetryVersion = poetry --version
    Write-Host "Poetry is installed: $poetryVersion"
} catch {
    Write-Host "Installing Poetry..."
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
    $env:Path += ";$env:APPDATA\Python\Scripts"
}

# Install dependencies
Write-Host "Installing project dependencies..."
poetry install --with dev

# Run tests
Write-Host "Running tests..."
poetry run pytest

Write-Host "Test setup complete!" 