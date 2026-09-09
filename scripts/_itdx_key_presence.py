"""Report whether Google Maps / MINDEX keys exist. Never print secret values."""

from __future__ import annotations

import os
from pathlib import Path

NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "MINDEX_API_KEY",
)

FILES = (
    Path(__file__).resolve().parents[1] / ".credentials.local",
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[1] / ".env.local",
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\.env"),
)


def main() -> None:
    print("FILE_EXISTS")
    for path in FILES:
        print(f"  {path.exists()} {path}")
    found: dict[str, list[tuple[str, bool, int]]] = {}
    for path in FILES:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"  read_fail {path.name} {type(exc).__name__}")
            continue
        for line in text.splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in NAMES:
                found.setdefault(key, []).append((path.name, bool(value), len(value)))
    print("KEY_PRESENT")
    for name in NAMES:
        rows = found.get(name, [])
        if not rows:
            print(f"  {name}: MISSING")
            continue
        for filename, nonempty, length in rows:
            print(f"  {name}: present={nonempty} len={length} file={filename}")
    print("PROCESS_ENV")
    for name in NAMES:
        value = os.environ.get(name, "")
        print(f"  {name}: set={bool(value)} len={len(value)}")


if __name__ == "__main__":
    main()
