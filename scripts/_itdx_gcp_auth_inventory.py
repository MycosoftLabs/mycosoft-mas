"""Inventory GCP auth surfaces. Never print secret values."""

from __future__ import annotations

from pathlib import Path

FILES = [
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local"),
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\credentials.local"),
]
WANT = {
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLOUD_PROJECT",
    "GCP_PROJECT",
    "GCLOUD_PROJECT",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_SERVICE_ACCOUNT_KEY",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_SERVICE_ACCOUNT_JSON_PATH",
}
MAPS = {
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
}


def main() -> None:
    for path in FILES:
        print("FILE", path.name, "exists", path.exists())
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in WANT:
                if "apps.googleusercontent.com" in value:
                    print(key, "PROJECT_NUMBER_PREFIX", value.split("-", 1)[0], "LEN", len(value))
                elif key.endswith("PATH") or key.endswith("CREDENTIALS"):
                    print(key, "SET", bool(value), "ABS", value[:3] if value else "")
                else:
                    print(key, "SET", "len", len(value), "json", value.startswith("{"))
            if key in MAPS and value:
                print(key, "PRESENT", "len", len(value), "prefix", value[:4])


if __name__ == "__main__":
    main()
