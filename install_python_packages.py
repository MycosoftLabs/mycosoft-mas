#!/usr/bin/env python3
"""
Install all required Python packages for Mycosoft MAS integrations.
"""
import subprocess
import sys

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Installing {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {description}: {e.stderr}")
        return False

def main():
    print("=" * 60)
    print("Installing Python Integration Packages")
    print("=" * 60)
    
    # Upgrade pip first
    print("\n[1/3] Upgrading pip...")
    run_command(f"{sys.executable} -m pip install --upgrade pip setuptools wheel", "pip")
    
    # Core packages from requirements.txt
    print("\n[2/3] Installing core packages from requirements.txt...")
    try:
        with open("requirements.txt", "r") as f:
            run_command(f"{sys.executable} -m pip install -r requirements.txt", "requirements.txt packages")
    except FileNotFoundError:
        print("⚠ requirements.txt not found, skipping...")
    
    # Integration packages
    print("\n[3/3] Installing integration packages...")
    integration_packages = [
        # Notion
        "notion-client>=2.2.1",
        # Asana
        "asana>=1.0.0",
        # Google Workspace
        "google-api-python-client>=2.100.0",
        "google-auth-httplib2>=0.1.1",
        "google-auth-oauthlib>=1.1.0",
        # Azure
        "azure-identity>=1.15.0",
        "azure-mgmt-resource>=23.0.0",
        "azure-mgmt-compute>=29.0.0",
        "azure-mgmt-storage>=21.0.0",
        "azure-storage-blob>=12.19.0",
        "azure-keyvault-secrets>=4.7.0",
        # Monitoring
        "prometheus-client>=0.19.0",
        # HTTP clients
        "httpx>=0.23.3",
        "aiohttp>=3.9.3",
        # Database
        "psycopg2-binary>=2.9.9",
        "redis>=5.0.1",
        "sqlalchemy>=2.0.23",
        "alembic>=1.11.1",
        # Core framework
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.0",
    ]
    
    failed = []
    for package in integration_packages:
        if not run_command(f"{sys.executable} -m pip install {package}", package.split(">=")[0]):
            failed.append(package)
    
    print("\n" + "=" * 60)
    print("Installation Summary")
    print("=" * 60)
    
    if failed:
        print(f"\n✗ Failed to install {len(failed)} packages:")
        for pkg in failed:
            print(f"  - {pkg}")
    else:
        print("\n✓ All packages installed successfully!")
    
    # Verify installations
    print("\nVerifying installations...")
    test_imports = [
        ("notion_client", "Notion"),
        ("asana", "Asana"),
        ("google.oauth2", "Google Workspace"),
        ("azure.identity", "Azure"),
        ("prometheus_client", "Prometheus"),
        ("redis", "Redis"),
        ("psycopg2", "PostgreSQL"),
        ("fastapi", "FastAPI"),
    ]
    
    verified = []
    failed_verify = []
    for module, name in test_imports:
        try:
            __import__(module)
            verified.append(name)
            print(f"✓ {name} SDK verified")
        except ImportError:
            failed_verify.append(name)
            print(f"✗ {name} SDK not found")
    
    print(f"\n✓ Verified: {len(verified)}/{len(test_imports)} packages")
    if failed_verify:
        print(f"✗ Failed verification: {', '.join(failed_verify)}")
    
    return len(failed) == 0 and len(failed_verify) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
