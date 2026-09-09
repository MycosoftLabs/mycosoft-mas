"""List env key NAMES that look like Google Maps. Never print values."""

from __future__ import annotations

from pathlib import Path

FILES = (
    Path(__file__).resolve().parents[1] / ".credentials.local",
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\.env"),
)

NEEDLES = ("GOOGLE", "MAPS", "GMAPS", "GCP_")


def main() -> None:
    for path in FILES:
        if not path.exists():
            continue
        print("FILE", path.name)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if any(n in key.upper() for n in NEEDLES):
                value = line.split("=", 1)[1].strip()
                print(f"  NAME={key} nonempty={bool(value)} len={len(value)}")


if __name__ == "__main__":
    main()
