"""Ensure empty FUSARIUM_GOOGLE_MAPS_API_KEY line exists. Never print values."""

from __future__ import annotations

from pathlib import Path

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
NAME = "FUSARIUM_GOOGLE_MAPS_API_KEY"


def main() -> None:
    text = CREDS.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith(f"{NAME}=") or line.strip().startswith(f"{NAME}="):
            value = line.split("=", 1)[1].strip()
            print("PLACEHOLDER exists=True nonempty=", bool(value))
            return
    if text and not text.endswith("\n"):
        text += "\n"
    text += f"# Re-paste newest Fusarium Maps key (Directions/Distance Matrix). Never commit.\n{NAME}=\n"
    CREDS.write_text(text, encoding="utf-8")
    print("PLACEHOLDER appended empty")


if __name__ == "__main__":
    main()
