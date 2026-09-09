"""Verify local Maps/Fusarium line numbers. No values printed."""

from __future__ import annotations

import hashlib
from pathlib import Path

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
NAMES = {
    "FUSARIUM_GOOGLE_MAPS_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
    "GOOGLE_API_KEY",
}


def main() -> None:
    lines = CREDS.read_text(encoding="utf-8", errors="replace").splitlines()
    print("LINE_COUNT", len(lines))
    for idx, line in enumerate(lines, start=1):
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name not in NAMES and not ("FUSARIUM" in name.upper() and "GOOGLE" in name.upper()):
            continue
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "-"
        print(f"line={idx} {name} len={len(value)} sha256_12={digest} empty={value == ''}")


if __name__ == "__main__":
    main()
