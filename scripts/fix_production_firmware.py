#!/usr/bin/env python3
"""
Fix MycoBrain Production Firmware for ArduinoJson v7 compatibility
"""

import re
import sys

def fix_firmware(filepath):
    """Fix ArduinoJson v7 compatibility issues"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Replace DynamicJsonDocument with JsonDocument
    content = content.replace('DynamicJsonDocument', 'JsonDocument')
    
    # Fix 2: Fix sendError calls with two arguments
    # Pattern: sendError("cmd", "message") -> sendError("cmd: message")
    def fix_send_error(match):
        cmd = match.group(1)
        msg = match.group(2)
        return f'sendError("{cmd}: {msg}")'
    
    content = re.sub(r'sendError\("([^"]+)",\s*"([^"]+)"\)', fix_send_error, content)
    
    # Fix 3: Add sendNDJSON function if missing
    if 'void sendNDJSON' not in content:
        # Find where to insert (after sendAck function)
        send_ndjson_func = '''
void sendNDJSON(JsonDocument& doc) {
  if (currentMode == MODE_MACHINE || jsonFormat) {
    serializeJson(doc, Serial);
    Serial.println();
  } else {
    serializeJsonPretty(doc, Serial);
    Serial.println();
  }
}
'''
        # Insert after sendAck function
        ack_pattern = r'(void sendAck\([^)]+\)\s*\{[^}]+\})'
        if re.search(ack_pattern, content):
            content = re.sub(ack_pattern, r'\1\n' + send_ndjson_func, content, count=1)
        else:
            # Insert before sendResponse
            content = re.sub(r'(void sendResponse)', send_ndjson_func + r'\n\1', content, count=1)
    
    # Fix 4: Fix sendResponse function signature
    # Change: void sendResponse(String type, DynamicJsonDocument& doc)
    # To: void sendResponse(String type, JsonDocument& doc)
    content = re.sub(r'void sendResponse\(String type,\s*DynamicJsonDocument&', 
                     'void sendResponse(String type, JsonDocument&', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")
    return True

if __name__ == "__main__":
    filepath = "firmware/MycoBrain_SideA/MycoBrain_SideA_Production.ino"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    fix_firmware(filepath)
    print("Firmware fixed!")
