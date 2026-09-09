"""Create empty FormSpace NLM drop folder on the shared NAS. No GGUF. No secrets printed."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
NAS_HOST = "192.168.0.105"
SHARE = "mycosoft.com"
NLM_REL = Path("models") / "nlm"
README_SRC = Path(__file__).resolve().parents[1] / "docs" / "formspace_nlm_nas" / "README.md"


def load_creds() -> None:
    if not CREDS.exists():
        raise SystemExit("missing .credentials.local")
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_creds()
    user = os.environ.get("NAS_SMB_USER") or ""
    password = os.environ.get("NAS_SMB_PASSWORD") or ""
    if not user or not password:
        print("NAS SMB credentials missing")
        return 2

    unc = f"\\\\{NAS_HOST}\\{SHARE}"
    # Reuse an existing mapping if a sibling already mounted the share.
    result = subprocess.run(
        ["cmd", "/c", "net", "use"],
        capture_output=True,
        text=True,
        check=False,
    )
    already = unc.lower() in (result.stdout or "").lower()
    if not already:
        mapped = subprocess.run(
            ["cmd", "/c", "net", "use", unc, password, f"/user:{user}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if mapped.returncode != 0:
            print("NAS map failed; sibling may still be claiming the mount. Wait and retry.")
            print((mapped.stderr or mapped.stdout or "")[:400].replace(password, "<redacted>"))
            return mapped.returncode

    nlm_dir = Path(unc) / NLM_REL
    incoming = nlm_dir / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    readme = nlm_dir / "README.md"
    if README_SRC.exists():
        shutil.copyfile(README_SRC, readme)
    else:
        readme.write_text(
            "Waiting for Morgan FormSpace NLM weights. No GGUF. See MAS docs Stages A-B.\n",
            encoding="utf-8",
        )

    names = sorted(p.name for p in nlm_dir.iterdir())
    extras = [name for name in names if name.lower() not in {"readme.md", "incoming"}]
    incoming_names = [p.name for p in incoming.iterdir()] if incoming.exists() else []
    print("NLM_DIR", str(nlm_dir))
    print("NAMES", names)
    print("INCOMING", incoming_names)
    if extras:
        print("WARN unexpected entries remain; did not delete sibling work")
    if any(name.lower().endswith(".gguf") for name in incoming_names + extras):
        print("ERROR GGUF found under models/nlm — do not load; move to models/myca")
        return 3
    print("READY_FOR_WEIGHTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
