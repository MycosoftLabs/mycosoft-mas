"""Restore tiles-only alias from website env. Never print values."""

from __future__ import annotations

import hashlib
from pathlib import Path

MAS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
WEB = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local")
TILES_NAME = "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY"
CANON_HASH = "da37efa21333"


def parse_one(path: Path, name: str) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return ""


def main() -> None:
    web = parse_one(WEB, TILES_NAME)
    mas = parse_one(MAS, TILES_NAME)
    web_hash = hashlib.sha256(web.encode("utf-8")).hexdigest()[:12] if web else "-"
    mas_hash = hashlib.sha256(mas.encode("utf-8")).hexdigest()[:12] if mas else "-"
    print("WEB_TILES len", len(web), "sha256_12", web_hash)
    print("MAS_TILES len", len(mas), "sha256_12", mas_hash)
    if not web or web_hash != CANON_HASH:
        print("ABORT web tiles not canonical")
        return
    if mas == web:
        print("TILES_ALREADY_OK")
        return
    lines = MAS.read_text(encoding="utf-8", errors="replace").splitlines()
    ended_nl = MAS.read_text(encoding="utf-8", errors="replace").endswith("\n")
    out: list[str] = []
    found = False
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#") and line.split("=", 1)[0].strip() == TILES_NAME:
            out.append(f"{TILES_NAME}={web}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{TILES_NAME}={web}")
    text = "\n".join(out) + ("\n" if ended_nl else "")
    MAS.write_text(text, encoding="utf-8")
    print("RESTORED_TILES from website was", mas_hash, "len", len(mas), "now", CANON_HASH, "len", len(web))


if __name__ == "__main__":
    main()
