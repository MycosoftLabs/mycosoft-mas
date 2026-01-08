#!/usr/bin/env python3
"""
Fix ArduinoJson v7 compatibility - replace JsonDocument(size) with StaticJsonDocument<size>
"""

import re
import sys

def fix_json_v7(filepath):
    """Fix JsonDocument(size) to StaticJsonDocument<size>"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix: JsonDocument doc(1024) -> StaticJsonDocument<1024> doc;
    # Pattern: JsonDocument <name>(<size>);
    def replace_json_doc(match):
        name = match.group(1)
        size = match.group(2)
        return f'StaticJsonDocument<{size}> {name};'
    
    content = re.sub(r'JsonDocument\s+(\w+)\((\d+)\);', replace_json_doc, content)
    
    # Also fix function parameters: JsonDocument& -> JsonDocument& (keep as is, but ensure StaticJsonDocument is used)
    # Actually, function parameters should stay as JsonDocument& since StaticJsonDocument inherits from JsonDocument
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")
    return True

if __name__ == "__main__":
    filepath = "firmware/MycoBrain_SideA/MycoBrain_SideA.ino"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    fix_json_v7(filepath)
    print("ArduinoJson v7 compatibility fixed!")
