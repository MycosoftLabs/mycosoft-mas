"""Fix BOM issues in all Python files and handle broken orchestrator.py"""
import os
import glob

def fix_bom(filepath):
    """Remove BOM from file if present."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check for UTF-8 BOM
        if content.startswith(b'\xef\xbb\xbf'):
            print(f"Fixing BOM in: {filepath}")
            content = content[3:]
            with open(filepath, 'wb') as f:
                f.write(content)
            return True
        # Check for UTF-16 LE BOM
        elif content.startswith(b'\xff\xfe'):
            print(f"Fixing UTF-16 LE BOM in: {filepath}")
            try:
                text = content[2:].decode('utf-16-le')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
                return True
            except:
                print(f"  Warning: Could not decode UTF-16 LE for {filepath}")
                return False
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def check_syntax(filepath):
    """Check if file has valid Python syntax."""
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
        return True
    except Exception as e:
        print(f"Syntax error in {filepath}: {e}")
        return False

# Delete the broken orchestrator.py at root level
broken_file = 'mycosoft_mas/orchestrator.py'
if os.path.exists(broken_file):
    print(f"Removing broken file: {broken_file}")
    os.remove(broken_file)
    print("  Removed successfully")

# Fix all Python files
fixed = 0
for filepath in glob.glob('mycosoft_mas/**/*.py', recursive=True):
    if fix_bom(filepath):
        fixed += 1

print(f"\nFixed {fixed} files with BOM issues")

# Check syntax of all files
print("\nChecking syntax of all files...")
errors = []
for filepath in glob.glob('mycosoft_mas/**/*.py', recursive=True):
    if not check_syntax(filepath):
        errors.append(filepath)

if errors:
    print(f"\n{len(errors)} files have syntax errors:")
    for e in errors:
        print(f"  - {e}")
else:
    print("\nAll files have valid syntax!")
