# Test environment setup script for Mycosoft MAS
Write-Host "Setting up test environment..."

# Create virtual environment
Write-Host "Creating Python virtual environment..."
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Python dependencies
Write-Host "Installing Python dependencies..."
pip install -r requirements.txt
poetry install

# Install Node.js dependencies
Write-Host "Installing Node.js dependencies..."
npm install

# Initialize PostgreSQL
Write-Host "Initializing PostgreSQL..."
$pgPath = "C:\Program Files\PostgreSQL\15\bin"
$env:Path += ";$pgPath"
initdb -D "C:\Program Files\PostgreSQL\15\data"
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" start

# Initialize Redis
Write-Host "Starting Redis server..."
Start-Service Redis

# Create necessary directories
Write-Host "Creating required directories..."
New-Item -ItemType Directory -Force -Path "logs"
New-Item -ItemType Directory -Force -Path "data"
New-Item -ItemType Directory -Force -Path "migrations"

# Copy configuration files
Write-Host "Setting up configuration files..."
Copy-Item "config.yaml.example" "config.yaml" -Force
Copy-Item ".env.example" ".env" -Force

# Run database migrations
Write-Host "Running database migrations..."
python -m alembic upgrade head

# Run tests
Write-Host "Running initial test suite..."
python -m pytest

Write-Host "Test environment setup completed!" 