"""Check syntax of all Python files in mycosoft_mas."""
import py_compile
import glob
import sys

errors = []
checked = 0

for filepath in glob.glob('mycosoft_mas/**/*.py', recursive=True):
    # Skip venv
    if 'venv' in filepath or 'site-packages' in filepath:
        continue
    
    checked += 1
    try:
        py_compile.compile(filepath, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append((filepath, str(e)))
    except Exception as e:
        errors.append((filepath, str(e)))

print(f"Checked {checked} files")

if errors:
    print(f"\n{len(errors)} files have syntax errors:")
    for filepath, error in errors:
        # Truncate long error messages
        error_short = error[:200] + "..." if len(error) > 200 else error
        print(f"\n  {filepath}:")
        print(f"    {error_short}")
    sys.exit(1)
else:
    print("All files have valid syntax!")
    sys.exit(0)
