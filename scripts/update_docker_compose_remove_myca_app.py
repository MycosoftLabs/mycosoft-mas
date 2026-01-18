#!/usr/bin/env python3
"""Remove myca-app service from docker-compose.yml"""

from pathlib import Path
import re

compose_file = Path("docker-compose.yml")

if not compose_file.exists():
    print(f"ERROR: {compose_file} not found")
    exit(1)

print("=" * 80)
print("REMOVING myca-app SERVICE FROM docker-compose.yml")
print("=" * 80)

# Read file
content = compose_file.read_text()

# Find myca-app service block
pattern = r'\n\s*myca-app:\s*\n(?:\s+[^\n]+\n)*'

matches = list(re.finditer(pattern, content))

if not matches:
    print("\n[INFO] No myca-app service found in docker-compose.yml")
    print("       Service may have already been removed.")
    exit(0)

print(f"\n[FOUND] {len(matches)} myca-app service definition(s)")

# Remove the service block
for match in matches:
    service_block = match.group(0)
    print(f"\n[REMOVING] Service block ({len(service_block)} characters):")
    print("-" * 80)
    # Show first few lines of the block
    lines = service_block.strip().split('\n')[:5]
    for line in lines:
        print(f"  {line}")
    if len(service_block.strip().split('\n')) > 5:
        print("  ...")
    print("-" * 80)
    
    content = content[:match.start()] + content[match.end():]

# Write back
compose_file.write_text(content)

print("\n[OK] docker-compose.yml updated successfully")
print("\n[NOTE] You should review the file to ensure no syntax errors were introduced")
