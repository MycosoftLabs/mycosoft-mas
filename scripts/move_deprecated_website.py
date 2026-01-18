#!/usr/bin/env python3
"""Move deprecated mycosoft-mas website files to deprecated folder."""

import os
import shutil
from pathlib import Path

mas_repo = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
deprecated_dir = mas_repo / "_deprecated_mas_website"

print("=" * 80)
print("MOVING DEPRECATED MAS WEBSITE FILES")
print("=" * 80)

# Files and directories to move
files_to_move = [
    "app",
    "components",
    "lib",
    "public",
    "styles",
    "package.json",
    "package-lock.json",
    "next.config.js",
    "next-env.d.ts",
    "tsconfig.json",
    "tailwind.config.js",
    "eslint.config.mjs",
    "middleware.ts",
]

# Create deprecated directory
print(f"\n1. Creating deprecated directory: {deprecated_dir}")
deprecated_dir.mkdir(exist_ok=True)
print("   [OK] Directory created")

# Move files
print("\n2. Moving files to deprecated directory:")
print("-" * 80)

moved_count = 0
for item in files_to_move:
    source = mas_repo / item
    dest = deprecated_dir / item
    
    if source.exists():
        try:
            if source.is_dir():
                shutil.move(str(source), str(dest))
                print(f"   [MOVED] {item}/ (directory)")
            else:
                shutil.move(str(source), str(dest))
                print(f"   [MOVED] {item}")
            moved_count += 1
        except Exception as e:
            print(f"   [ERROR] {item}: {str(e)}")
    else:
        print(f"   [SKIP] {item} (not found)")

print(f"\n3. Summary: Moved {moved_count} items to deprecated folder")

# Create README in deprecated folder
readme_content = """# DEPRECATED - DO NOT USE

This folder contains the old Mycosoft-MAS website that was interfering with 
the actual Mycosoft Website development.

## What This Was

This was a Next.js application that:
- Hijacked port 3000 during development
- Showed a "Mycosoft MAS" homepage instead of the real website
- Was NOT the UniFi dashboard for agent management
- Was NOT the actual Mycosoft Website

## Why It's Deprecated

- The actual Mycosoft Website is in: `C:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\WEBSITE\\website`
- This caused port conflicts and confusion during development
- It was never authorized by the user

## What Should Be Used Instead

- **Actual Website**: `C:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\WEBSITE\\website`
- **UniFi Dashboard**: `mycosoft-mas/unifi-dashboard/` (for agent management)

## DO NOT RESTORE THESE FILES

Do not move these files back or use them in development. They are kept
here only for reference and should never be accessed.

---
Deprecated: January 17, 2026
"""
readme_file = deprecated_dir / "README.md"
readme_file.write_text(readme_content)
print(f"   [CREATED] README.md in deprecated folder")

# Update .gitignore to exclude if not already
gitignore_path = mas_repo / ".gitignore"
if gitignore_path.exists():
    gitignore_content = gitignore_path.read_text()
    if "_deprecated_mas_website" not in gitignore_content:
        gitignore_path.write_text(gitignore_content + "\n# Deprecated MAS website\n_deprecated_mas_website/\n")
        print(f"   [UPDATED] .gitignore to exclude deprecated folder")
else:
    gitignore_path.write_text("# Deprecated MAS website\n_deprecated_mas_website/\n")
    print(f"   [CREATED] .gitignore to exclude deprecated folder")

print("\n" + "=" * 80)
print("DEPRECATED WEBSITE FILES MOVED SUCCESSFULLY")
print("=" * 80)
print(f"\nLocation: {deprecated_dir}")
print("\nThese files will not be accessed during development.")
