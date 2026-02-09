"""Find all corrupted Python files that need regeneration."""
import os
import glob
import py_compile

corrupted = []
for filepath in glob.glob('mycosoft_mas/**/*.py', recursive=True):
    try:
        # Try to compile it
        py_compile.compile(filepath, doraise=True)
    except Exception:
        # Try to read and check if it's valid UTF-8
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Check for obvious corruption
            if '\x00' in content or '\ufeff' in content[1:] or '\u2222' in content:
                corrupted.append(filepath)
        except:
            corrupted.append(filepath)

print(f"Found {len(corrupted)} corrupted files:")
for f in sorted(corrupted):
    print(f"  - {f}")
