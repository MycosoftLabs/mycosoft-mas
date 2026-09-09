"""Inspect/fix Maps key paste. Never print key values."""

from __future__ import annotations

import hashlib
from pathlib import Path

MAS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
WEB = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local")
WANT = (
    "FUSARIUM_GOOGLE_MAPS_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)
TILES_HASH = "da37efa21333"
EXPIRED_AI_HASH = "377c33611a56"


def parse(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        out[name.strip()] = value.strip().strip('"').strip("'")
    return out


def report(label: str, env: dict[str, str]) -> None:
    print("FILE", label)
    for name in WANT:
        value = env.get(name)
        if value is None:
            print(f"  {name} present=False")
            continue
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "-"
        aiza = value.startswith("AIza")
        truncated = (not value) or (aiza and len(value) < 35) or (aiza and len(value) != 39)
        print(
            f"  {name} present=True len={len(value)} sha256_12={digest} "
            f"starts_AIza={aiza} looks_truncated={truncated}"
        )


def upsert(path: Path, name: str, value: str) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key == name:
            out.append(f"{name}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{name}={value}")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return "updated" if found else "appended"


def main() -> None:
    mas = parse(MAS)
    web = parse(WEB)
    report("MAS .credentials.local", mas)
    report("website .env.local", web)
    web_tiles = web.get("NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY") or ""
    web_digest = hashlib.sha256(web_tiles.encode("utf-8")).hexdigest()[:12] if web_tiles else "-"
    print("WEB_TILES sha256_12", web_digest, "len", len(web_tiles), "starts_AIza", web_tiles.startswith("AIza"))

    if web_tiles and web_digest == TILES_HASH:
        tiles_aliases = ("NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",)
        for name in tiles_aliases:
            current = mas.get(name) or ""
            cur_hash = hashlib.sha256(current.encode("utf-8")).hexdigest()[:12] if current else "-"
            if current != web_tiles:
                action = upsert(MAS, name, web_tiles)
                print("RESTORE_TILES", name, action, "was", cur_hash, "now", TILES_HASH)
            else:
                print("TILES_OK", name, TILES_HASH)
    else:
        print("WEB_TILES_NOT_CANONICAL", web_digest)

    mas = parse(MAS)
    fusarium = mas.get("FUSARIUM_GOOGLE_MAPS_API_KEY") or ""
    fus_hash = hashlib.sha256(fusarium.encode("utf-8")).hexdigest()[:12] if fusarium else "-"
    fus_ok = (
        bool(fusarium)
        and fusarium.startswith("AIza")
        and len(fusarium) >= 35
        and fus_hash not in {TILES_HASH, EXPIRED_AI_HASH}
    )
    print(
        "FUSARIUM_VERDICT",
        "OK_DISTINCT" if fus_ok else "BAD_DO_NOT_USE_ON_188",
        "sha256_12",
        fus_hash,
    )


if __name__ == "__main__":
    main()
