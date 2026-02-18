"""
Start MYCA Voice – backward-compatible launcher (Feb 2026)

This script delegates to the single voice-system script.
Use:  python scripts/start_voice_system.py
"""
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_start_voice = os.path.join(_SCRIPT_DIR, "start_voice_system.py")
if not os.path.isfile(_start_voice):
    print("[ERROR] start_voice_system.py not found", file=sys.stderr)
    sys.exit(1)
os.execv(sys.executable, [sys.executable, _start_voice] + sys.argv[1:])
