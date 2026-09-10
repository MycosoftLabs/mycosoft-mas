"""Copy archived FormSpace reference to NAS models/nlm/reference. No 188 root writes."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
SRC = Path(
    r"C:\Users\Owner1\Downloads\NLM_Weights_MAS188_Cursor_Package"
    r"\NLM_Weights_MAS188_Cursor_Package\reference"
)
EXPECTED_WEIGHTS = "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2"
UNC = r"\\192.168.0.105\mycosoft.com"


def load_creds() -> None:
    if not CREDS.exists():
        raise SystemExit("missing .credentials.local")
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    load_creds()
    user = os.environ.get("NAS_SMB_USER") or ""
    password = os.environ.get("NAS_SMB_PASSWORD") or ""
    if not user or not password:
        print("NAS SMB credentials missing")
        return 2
    if not SRC.is_dir():
        print("SOURCE_MISSING")
        return 3
    mapped = subprocess.run(
        ["cmd", "/c", "net", "use", UNC, password, f"/user:{user}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if mapped.returncode != 0 and "already" not in (mapped.stderr or mapped.stdout or "").lower():
        print("NAS_MAP_FAILED")
        print((mapped.stderr or mapped.stdout or "")[:300].replace(password, "<redacted>"))
        return mapped.returncode
    dest = Path(UNC) / "models" / "nlm" / "reference"
    incoming = Path(UNC) / "models" / "nlm" / "incoming"
    dest.mkdir(parents=True, exist_ok=True)
    incoming.mkdir(parents=True, exist_ok=True)
    src_weights = SRC / "weights.pt"
    if src_weights.is_file() and sha256(src_weights) != EXPECTED_WEIGHTS:
        print("SOURCE_HASH_MISMATCH")
        return 4
    dest_weights = dest / "weights.pt"
    if dest_weights.is_file() and sha256(dest_weights) != EXPECTED_WEIGHTS:
        print("DEST_HASH_PRESERVED_DIFFERENT")
        return 5
    copied = []
    for item in SRC.iterdir():
        if not item.is_file():
            continue
        target = dest / item.name
        if target.is_file() and sha256(target) == sha256(item):
            copied.append(f"{item.name}=already")
            continue
        shutil.copy2(item, target)
        copied.append(f"{item.name}=copied")
    checksums = dest / "CHECKSUMS_SEP10_2026.txt"
    lines = []
    for item in sorted(dest.iterdir()):
        if item.is_file() and item.name != checksums.name:
            lines.append(f"{sha256(item)}  {item.name}")
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    readme = incoming / "README_SEP10_2026.txt"
    if not readme.exists():
        readme.write_text(
            "incoming/ is for NEW forecast artifacts only.\n"
            "The archived SYNTHETIC_TEST checkpoint lives in reference/.\n"
            "Do not treat SHA 0c5fb815 as a production forecast.\n",
            encoding="utf-8",
        )
    print("DEST", dest)
    print("COPIED", copied)
    print("WEIGHTS", sha256(dest / "weights.pt") if (dest / "weights.pt").is_file() else "missing")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
