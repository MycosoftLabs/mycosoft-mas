#!/usr/bin/env python3
"""Apply proprietary LICENSE, NOTICE, and README license sections across Mycosoft repos."""

from __future__ import annotations

import re
from pathlib import Path

CODE_ROOT = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE")

LICENSE_TEXT = """PROPRIETARY SOFTWARE LICENSE

Copyright (c) 2022-2026 Mycosoft, Inc. All Rights Reserved.

This software, including all source code, object code, documentation, designs,
schematics, data, models, weights, and associated materials (collectively, the
"Software"), is the proprietary and confidential property of Mycosoft, Inc.
("Mycosoft") and is protected by United States and international copyright,
trade secret, and other intellectual property laws.

NO LICENSE GRANTED. No license, right, or permission -- whether express,
implied, by estoppel, or otherwise -- is granted to any person or entity to
use, access, copy, reproduce, modify, adapt, translate, merge, publish,
distribute, sublicense, sell, create derivative works from, reverse engineer,
decompile, disassemble, or otherwise exploit the Software, in whole or in part,
without the prior written authorization of Mycosoft, executed by a duly
authorized officer of Mycosoft.

CONFIDENTIALITY. The Software constitutes the confidential information and
trade secrets of Mycosoft. Any access to the Software transfers no ownership
interest whatsoever and imposes an obligation to maintain its confidentiality.

NO WARRANTY. The Software is provided "AS IS," without warranty of any kind,
express or implied.

EXPORT CONTROL. The Software may be subject to United States export control
laws and regulations, including the Export Administration Regulations (EAR,
15 C.F.R. Parts 730-774) and potentially the International Traffic in Arms
Regulations (ITAR, 22 C.F.R. Parts 120-130). The Software may not be exported,
re-exported, released, or disclosed to any foreign person or destination except
in full compliance with such laws. Unauthorized export is strictly prohibited.

U.S. GOVERNMENT / DEFENSE USE. Use by the U.S. Department of Defense, other
U.S. government agencies, or defense contractors is subject to applicable
federal law, acquisition regulations, and written agreement with Mycosoft.

CYBERSECURITY POSTURE. Mycosoft aligns engineering and security practices with
NIST cybersecurity frameworks and CMMC-oriented controls at the organizational
level. Presence of this notice does not constitute CMMC certification.

ENFORCEMENT. Unauthorized use, reproduction, or distribution of the Software,
or any portion thereof, may result in severe civil and criminal penalties and
will be prosecuted to the maximum extent possible under law.

CONTACT. All licensing and authorization inquiries: legal@mycosoft.org
"""

NOTICE_BASE = """Mycosoft, Inc. -- PROPRIETARY AND CONFIDENTIAL
Copyright (c) 2022-2026 Mycosoft, Inc. All Rights Reserved.

This repository and its contents are the proprietary property of Mycosoft, Inc.
and are licensed to no third party. All rights reserved. See LICENSE.

Portions of this codebase may relate to marine, acoustic, environmental sensing,
defense, or government operational technologies that could be subject to U.S.
export control laws (EAR / ITAR). Do not export, share, or disclose outside
Mycosoft, Inc. without prior written authorization and export-compliance review.

Unauthorized use is prohibited. Contact: legal@mycosoft.org
"""

README_HEADER = (
    "> **Proprietary — Mycosoft, Inc.** Authorized use only. "
    "See [LICENSE](./LICENSE) and [NOTICE](./NOTICE). "
    "U.S. defense/government and export-control terms may apply.\n"
)

README_LICENSE_SECTION = """---

## License and export control

**Proprietary — Mycosoft, Inc. All Rights Reserved.**

This repository is proprietary software. No use, copy, modification, distribution,
or disclosure is permitted without **prior written authorization** from Mycosoft, Inc.

- See [LICENSE](./LICENSE) and [NOTICE](./NOTICE) in this repository.
- Portions may relate to U.S. defense, government, marine, acoustic, or environmental
  sensing use cases subject to applicable law, including **EAR** and potentially **ITAR**
  export controls. This repository is **not** marked as ITAR-classified unless explicitly
  labeled elsewhere.
- Mycosoft aligns engineering and security practices with **NIST** cybersecurity
  frameworks and **CMMC**-oriented controls at the organizational level; no certification
  is claimed by presence of this notice alone.
- U.S. Department of Defense and government use is subject to applicable federal law
  and contract terms.

**Contact:** legal@mycosoft.org
"""

REPOS: list[tuple[str, str | None]] = [
    ("MAS/mycosoft-mas", None),
    ("WEBSITE/website", None),
    ("MINDEX/mindex", None),
    ("mycobrain", None),
    ("NATUREOS/NatureOS", None),
    ("Mycorrhizae/mycorrhizae-protocol", None),
    ("MAS/NLM", None),
    ("MAS/sdk", None),
    ("platform-infra", None),
    ("MYCODAO", None),
    ("Devices/psathyrella-jetson", None),
]


def notice_for_repo(repo_label: str) -> str:
    extra = f"\nRepository: {repo_label}\n"
    return NOTICE_BASE + extra


def upsert_readme(readme_path: Path) -> bool:
    if not readme_path.exists():
        return False
    text = readme_path.read_text(encoding="utf-8")
    changed = False

    if "Proprietary — Mycosoft, Inc." not in text[:800]:
        lines = text.splitlines()
        insert_at = 1
        for i, line in enumerate(lines[1:6], start=1):
            if line.strip() and not line.startswith("#"):
                insert_at = i
                break
            if line.startswith("#") and i > 0:
                insert_at = i + 1
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, README_HEADER.rstrip())
        text = "\n".join(lines)
        if not text.endswith("\n"):
            text += "\n"
        changed = True

    license_pattern = re.compile(
        r"\n---\n\n## (?:📜 )?License(?: and export control)?\n[\s\S]*$",
        re.MULTILINE,
    )
    if license_pattern.search(text):
        new_text = license_pattern.sub("\n" + README_LICENSE_SECTION, text)
        if new_text != text:
            text = new_text
            changed = True
    elif "## License" not in text and "License and export control" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + README_LICENSE_SECTION + "\n"
        changed = True

    if changed:
        readme_path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def apply_repo(rel_path: str) -> dict[str, bool]:
    root = CODE_ROOT / rel_path.replace("/", "\\")
    results = {"license": False, "notice": False, "readme": False}
    if not root.is_dir():
        return results

    license_path = root / "LICENSE"
    if not license_path.exists() or license_path.read_text(encoding="utf-8") != LICENSE_TEXT:
        license_path.write_text(LICENSE_TEXT, encoding="utf-8", newline="\n")
        results["license"] = True

    notice_path = root / "NOTICE"
    notice_text = notice_for_repo(rel_path)
    if not notice_path.exists() or notice_path.read_text(encoding="utf-8") != notice_text:
        notice_path.write_text(notice_text, encoding="utf-8", newline="\n")
        results["notice"] = True

    readme = root / "README.md"
    if upsert_readme(readme):
        results["readme"] = True

    return results


def main() -> None:
    for rel, _ in REPOS:
        out = apply_repo(rel)
        print(f"{rel}: {out}")


if __name__ == "__main__":
    main()
