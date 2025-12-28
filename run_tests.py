import subprocess
import sys
import os
import shutil
from pathlib import Path

def find_python():
    """Auto-detect Python executable."""
    # Try common Python executable names
    for python_cmd in ["python", "python3", "py"]:
        python_path = shutil.which(python_cmd)
        if python_path:
            # Verify it's Python 3.x
            try:
                result = subprocess.run(
                    [python_path, "--version"],
                    capture_output=True,
                    text=True
                )
                if "Python 3" in result.stdout:
                    return python_path
            except:
                continue
    
    # Try common installation paths on Windows
    common_paths = [
        "C:\\Program Files\\Python313\\python.exe",
        "C:\\Program Files\\Python312\\python.exe",
        "C:\\Program Files\\Python311\\python.exe",
        "C:\\Program Files\\Python310\\python.exe",
        "C:\\Python313\\python.exe",
        "C:\\Python312\\python.exe",
        "C:\\Python311\\python.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Ensure we're in the project root
    os.chdir(project_root)
    
    try:
        # Auto-detect Python
        python_exe = find_python()
        
        if python_exe:
            print(f"Found Python at: {python_exe}")
            # Try to set up Poetry environment with detected Python
            try:
                subprocess.run(["poetry", "env", "use", python_exe], check=False)
            except:
                print("Could not set Poetry Python version, using default...")
        else:
            print("Using default Poetry Python environment...")
        
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