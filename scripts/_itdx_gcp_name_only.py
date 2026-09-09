"""Print presence of project-like env names. Never print values that look like keys."""

from __future__ import annotations

from pathlib import Path

FILES = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.env.local"),
]
NEEDLES = (
    "PROJECT",
    "GCP",
    "GOOGLE_CLOUD",
    "FIREBASE",
    "GCLOUD",
    "MAPS",
)


def main() -> None:
    for path in FILES:
        print("FILE", path, "exists", path.exists())
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if not any(n in name.upper() for n in NEEDLES):
                continue
            looks_key = value.startswith("AIza") or "BEGIN PRIVATE" in value or len(value) > 80
            safe = "KEYLIKE" if looks_key else ("idish" if value.replace("-", "").replace("_", "").isalnum() else "other")
            shown = ""
            if not looks_key and len(value) <= 64 and " " not in value and "/" not in value:
                shown = value
            print(f"  {name} set={bool(value)} len={len(value)} kind={safe}" + (f" value={shown}" if shown else ""))


if __name__ == "__main__":
    main()
