import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Ensure we're in the project root
    os.chdir(project_root)
    
    try:
        # First, ensure we're using Python 3.11
        print("Setting up Poetry environment with Python 3.11...")
        subprocess.run(["poetry", "env", "use", "C:\\Program Files\\Python311\\python.exe"], check=True)
        
        # Install dependencies using Poetry
        print("\nInstalling dependencies with Poetry...")
        subprocess.run(["poetry", "install", "--with", "dev"], check=True)
        
        # Run pytest with coverage using Poetry
        print("\nRunning tests...")
        result = subprocess.run([
            "poetry", "run", "pytest",
            "tests/",
            "-v",
            "--cov=mycosoft_mas",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
        
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e.cmd}")
        print(f"Exit code: {e.returncode}")
        if e.output:
            print(f"Output: {e.output.decode()}")
        if e.stderr:
            print(f"Error: {e.stderr.decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 