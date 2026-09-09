"""rg-style name hunt for Fusarium/Google env vars. No values printed."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\platform-infra"),
    Path(r"C:\Users\Owner1\.cursor\plans"),
]
PATTERNS = (
    "FUSARIUM_",
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS",
    "GOOGLE_MAPS_KEY",
    "FUSARIUM_GOOGLE",
)


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    for root in ROOTS:
        if not root.exists():
            print("ABSENT", root)
            continue
        print("ROOT", root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".next", "dist", "__pycache__"}]
            for name in filenames:
                if name.endswith((".png", ".jpg", ".webp", ".mp4", ".zip", ".pyc")):
                    continue
                path = Path(dirpath) / name
                try:
                    if path.stat().st_size > 800_000:
                        continue
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                hits = [p for p in PATTERNS if p in text]
                if not hits:
                    continue
                # Only report env-like assignments
                printed = False
                for line in text.splitlines():
                    if "=" not in line:
                        continue
                    var = line.split("=", 1)[0].strip().lstrip("#").strip()
                    if not any(p in var for p in PATTERNS) and "FUSARIUM" not in var.upper():
                        continue
                    if "GOOGLE" not in var.upper() and "MAPS" not in var.upper() and "FUSARIUM" not in var.upper():
                        continue
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if not value or value.startswith("http") or " " in value[:8]:
                        # likely prose
                        if not var.replace("_", "").isalnum():
                            continue
                    if not printed:
                        print("FILE", iso_mtime(path), path)
                        printed = True
                    if value.startswith("AIza"):
                        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                        print(f"  {var} AIza len={len(value)} sha256_12={digest}")
                    elif value and len(value) < 80 and not any(c.isspace() for c in value[:20]):
                        print(f"  {var} set=True len={len(value)} prefix={value[:4] if len(value)>=4 else 'NONE'}")
                    else:
                        print(f"  {var} mention_or_empty")


if __name__ == "__main__":
    main()
