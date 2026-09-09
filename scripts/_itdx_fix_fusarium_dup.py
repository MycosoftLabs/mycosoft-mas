"""Fix duplicate Fusarium Maps lines. Never print key values."""

from __future__ import annotations

import hashlib
from pathlib import Path

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
CANON = "FUSARIUM_GOOGLE_MAPS_API_KEY"
TILES = "da37efa21333"


def main() -> None:
    raw = CREDS.read_text(encoding="utf-8", errors="replace")
    ended_nl = raw.endswith("\n")
    lines = raw.splitlines()
    print("LINE_COUNT", len(lines))
    hits: list[tuple[int, str, int, str, bool]] = []
    for idx, line in enumerate(lines, start=1):
        if not line or line.lstrip().startswith("#") or "=" not in line:
            if "FUSARIUM" in line.upper() and "GOOGLE" in line.upper():
                print(f"COMMENT {idx} fusarium_mention")
            continue
        name = line.split("=", 1)[0].strip()
        value = line.split("=", 1)[1].strip().strip('"').strip("'")
        upper = name.upper()
        if "FUSARIUM" in upper and "GOOGLE" in upper:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "-"
            hits.append((idx, name, len(value), digest, value.startswith("AIza")))
            print(
                f"HIT line={idx} name={name} len={len(value)} sha256_12={digest} "
                f"AIza={value.startswith('AIza')} empty={value == ''}"
            )
        if name in {
            "GOOGLE_MAPS_API_KEY",
            "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
            "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
            "GOOGLE_API_KEY",
        }:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "-"
            print(f"MAPS line={idx} name={name} len={len(value)} sha256_12={digest}")

    nonempty = [h for h in hits if h[2] > 0]
    empty = [h for h in hits if h[2] == 0]
    print("NONEMPTY", len(nonempty), "EMPTY", len(empty))
    if not nonempty:
        print("NO_NONEMPTY_FUSARIUM")
        return
    keep_idx, keep_name, keep_len, keep_hash, keep_aiza = nonempty[-1]
    if 127 <= len(lines):
        last = lines[126]
        if "=" in last and not last.lstrip().startswith("#"):
            last_name = last.split("=", 1)[0].strip()
            last_val = last.split("=", 1)[1].strip().strip('"').strip("'")
            if last_val:
                keep_idx = 127
                keep_name = last_name
                keep_len = len(last_val)
                keep_hash = hashlib.sha256(last_val.encode("utf-8")).hexdigest()[:12]
                keep_aiza = last_val.startswith("AIza")
                print(
                    "KEEP_LINE_127 name",
                    keep_name,
                    "len",
                    keep_len,
                    "sha256_12",
                    keep_hash,
                    "AIza",
                    keep_aiza,
                )
    keep_line = lines[keep_idx - 1]
    keep_value = keep_line.split("=", 1)[1].strip().strip('"').strip("'")
    out: list[str] = []
    skipped_empty = 0
    skipped_extra = 0
    wrote_canon = False
    for idx, line in enumerate(lines, start=1):
        if line.lstrip().startswith("#") and "Re-paste newest Fusarium Maps key" in line:
            skipped_empty += 1
            continue
        if "=" in line and not line.lstrip().startswith("#"):
            name = line.split("=", 1)[0].strip()
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if "FUSARIUM" in name.upper() and "GOOGLE" in name.upper():
                if not value:
                    skipped_empty += 1
                    continue
                if idx != keep_idx:
                    skipped_extra += 1
                    continue
                out.append(f"{CANON}={keep_value}")
                wrote_canon = True
                continue
        out.append(line)
    if not wrote_canon:
        out.append(f"{CANON}={keep_value}")
    text = "\n".join(out)
    if ended_nl:
        text += "\n"
    CREDS.write_text(text, encoding="utf-8")
    print(
        "WROTE kept_sha256_12",
        keep_hash,
        "same_as_tiles",
        keep_hash == TILES,
        "skipped_empty",
        skipped_empty,
        "skipped_extra",
        skipped_extra,
        "new_line_count",
        len(out),
    )


if __name__ == "__main__":
    main()
