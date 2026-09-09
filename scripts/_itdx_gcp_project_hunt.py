"""Hunt GCP project IDs in local files. Never print API keys or private keys."""

from __future__ import annotations

import json
import re
from pathlib import Path

AIZA_RE = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
WANT = re.compile(
    r"(GCP_PROJECT|GOOGLE_CLOUD_PROJECT|GCLOUD_PROJECT|GOOGLE_CLOUD_PROJECT_ID|"
    r"project_id|console\.cloud\.google\.com/[^\s)\"']+)",
    re.I,
)
ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE"),
]


def main() -> None:
    files: list[Path] = []
    for root in ROOTS:
        for name in (".credentials.local", ".env.local", ".env"):
            path = root / name
            if path.is_file():
                files.append(path)
        docs = root / "docs"
        if docs.is_dir():
            files.extend(docs.glob("*GCP*"))
            files.extend(docs.glob("*GOOGLE*"))
            files.extend(docs.glob("*MAPS*"))
            files.extend(docs.glob("*ITDX*SEP09*"))
    for root in ROOTS[:2]:
        files.extend(root.glob("**/service_account.json"))
        files.extend(root.glob("**/*gcp*credentials*.json"))
    seen: set[str] = set()
    for path in files:
        key = str(path)
        if key in seen or not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        seen.add(key)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.suffix == ".json" and "private_key" in text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                print("FILE", path, "SA_JSON_UNPARSED")
                continue
            print("FILE", path.name, "SA_PROJECT", data.get("project_id"), "SA_EMAIL_LOCAL", str(data.get("client_email") or "").split("@", 1)[0])
            continue
        hits: list[str] = []
        for line in text.splitlines():
            if not WANT.search(line) or "AIza" in line:
                continue
            snippet = AIZA_RE.sub("AIza***", line.strip())
            if any(token in snippet.upper() for token in ("KEY", "SECRET", "PASSWORD", "TOKEN", "PRIVATE")):
                name = snippet.split("=", 1)[0]
                hits.append(f"{name}=REDACTED")
            else:
                hits.append(snippet[:200])
        if hits:
            print("FILE", path)
            for hit in hits[:15]:
                print(" ", hit)
    print("SCANNED", len(seen))


if __name__ == "__main__":
    main()
