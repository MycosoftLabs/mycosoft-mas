#!/usr/bin/env python3
"""Find and document the interfering mycosoft-mas website structure."""

import os
from pathlib import Path

mas_repo = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")

print("=" * 80)
print("MYCOSOFT-MAS WEBSITE STRUCTURE ANALYSIS")
print("=" * 80)

# Find Next.js app files
nextjs_files = [
    "package.json",
    "next.config.js",
    "tsconfig.json",
    "tailwind.config.js",
    ".eslintrc.json",
    "app/",
    "components/",
    "lib/",
    "public/",
    "styles/",
]

print("\n1. NEXT.JS APPLICATION FILES:")
print("-" * 80)
for file in nextjs_files:
    path = mas_repo / file
    if path.exists():
        if path.is_dir():
            files = list(path.rglob("*"))[:10]  # First 10 files
            file_count = len(list(path.rglob("*")))
            print(f"  [FOUND] {file}/ ({file_count} files)")
            for f in files[:5]:
                print(f"      - {f.relative_to(mas_repo)}")
            if len(list(path.rglob("*"))) > 5:
                print(f"      ... and {len(list(path.rglob('*'))) - 5} more")
        else:
            print(f"  [FOUND] {file}")
    else:
        print(f"  [MISSING] {file} (NOT FOUND)")

# Check package.json
print("\n2. PACKAGE.JSON DETAILS:")
print("-" * 80)
package_json = mas_repo / "package.json"
if package_json.exists():
    import json
    with open(package_json) as f:
        pkg = json.load(f)
    print(f"  Name: {pkg.get('name', 'N/A')}")
    print(f"  Version: {pkg.get('version', 'N/A')}")
    print(f"  Scripts: {list(pkg.get('scripts', {}).keys())}")

# Check app directory structure
print("\n3. APP DIRECTORY STRUCTURE:")
print("-" * 80)
app_dir = mas_repo / "app"
if app_dir.exists():
    for item in sorted(app_dir.iterdir()):
        if item.is_dir():
            pages = list(item.rglob("page.tsx"))
            routes = list(item.rglob("route.ts"))
            print(f"  {item.name}/")
            if pages:
                print(f"    Pages: {[str(p.relative_to(app_dir)) for p in pages]}")
            if routes:
                print(f"    Routes: {[str(r.relative_to(app_dir)) for r in routes]}")

# Check for port 3000/3001 references
print("\n4. PORT CONFIGURATION:")
print("-" * 80)
port_files = []
for ext in ["*.ts", "*.tsx", "*.js", "*.json", "*.yml", "*.yaml"]:
    for file in mas_repo.rglob(ext):
        try:
            if file.is_file() and file.stat().st_size < 100000:  # Skip large files
                content = file.read_text(errors='ignore')
                if "3000" in content or "3001" in content:
                    port_files.append(file)
        except:
            pass

for f in port_files[:10]:
    print(f"  {f.relative_to(mas_repo)}")

# Check docker-compose files
print("\n5. DOCKER COMPOSE CONFIGURATION:")
print("-" * 80)
for compose_file in ["docker-compose.yml", "docker-compose.always-on.yml"]:
    path = mas_repo / compose_file
    if path.exists():
        print(f"\n  {compose_file}:")
        content = path.read_text()
        if "3000" in content or "3001" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "3000" in line or "3001" in line or "myca-app" in line.lower() or "website" in line.lower():
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    print(f"    Line {i+1}:")
                    for j in range(start, end):
                        marker = ">>>" if j == i else "   "
                        print(f"    {marker} {j+1:4d}: {lines[j]}")

# Summary
print("\n6. SUMMARY:")
print("-" * 80)
print(f"  Root directory: {mas_repo}")
print(f"  This Next.js app is in: {mas_repo}")
print(f"  Main app directory: {mas_repo / 'app'}")
print(f"  Components: {mas_repo / 'components'}")
print(f"  This is NOT the UniFi dashboard (which is in: {mas_repo / 'unifi-dashboard'})")
print(f"\n  ⚠️  THIS IS THE INTERFERING WEBSITE THAT SHOULD BE DELETED")
