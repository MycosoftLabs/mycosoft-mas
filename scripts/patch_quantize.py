#!/usr/bin/env python3
"""Patch moshi quantize.py to auto-convert weight_scb dtype."""
import sys

# Read the original file
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

# Find and replace the RuntimeError block
patched = []
i = 0
while i < len(lines):
    line = lines[i]
    # Line 32: if state.SCB.dtype != torch.float:
    if 'if state.SCB.dtype != torch.float:' in line and 'raise RuntimeError' in ''.join(lines[i:i+5]):
        # Replace the if-raise block with auto-conversion
        patched.append(line)  # Keep the if line
        patched.append('            # PATCHED (Feb 13 2026): Auto-convert bfloat16 to float\n')
        patched.append('            state.SCB = state.SCB.float()\n')
        # Skip the raise RuntimeError lines (next 3-4 lines)
        i += 1
        while i < len(lines) and ('raise RuntimeError' in lines[i] or '                "' in lines[i] or '                "When' in lines[i] or '                "the model' in lines[i]):
            i += 1
        continue
    patched.append(line)
    i += 1

# Write patched version
with open(sys.argv[1], 'w') as f:
    f.writelines(patched)

print("Patched quantize.py: converted RuntimeError to auto-conversion")
