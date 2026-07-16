#!/usr/bin/env python3
"""Install/verify Mycosoft CUI Rules of Behavior across agent surfaces.

This tool manages repository instruction files only. It does not claim to modify
vendor account settings or make any AI service CUI-authorized.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

POLICY_SHA256 = "350442fb938e5e14114817e7ddfc08a16ecb84bf3a50b705977b4a68655beb19"
MARKER = "<!-- MYCOSOFT-CUI-POLICY:MYC-CUI-AI-ROB-1.0 -->"
BLOCK = f"""{MARKER}

## Mandatory CUI / CMMC gate

This agent operates outside the CUI boundary. No CUI, CTI, CDI, export-controlled technical data,
marked `CUI//...` material, covered-contract technical content, or secrets may enter prompts,
model calls, tools, logs, repositories, databases, or outputs. CUI remains only in PreVeil until
Morgan Rockcoons (SAO) authorizes a named in-boundary service and adds it to the SSP. When
classification is uncertain, stop and route to PreVeil. Never state that Mycosoft is CMMC compliant
or mark a practice Met without a real evidence URI and SAO validation. Humans submit government
filings. Use Morgan Rockcoons (SAO), RJ Ricasata (CFO), Mycosoft, LLC as the CMMC entity, and
Mycosoft, Inc. as sole-member parent. Policy SHA-256: `{POLICY_SHA256}`.

"""

MANAGED_FILES = {
    "AGENTS.md": "AGENTS.md",
    ".cursor/rules/000-cui-cmmc-hardline.mdc": ".cursor/rules/000-cui-cmmc-hardline.mdc",
    ".claude/rules/cui-cmmc-hardline.md": ".claude/rules/cui-cmmc-hardline.md",
    ".github/copilot-instructions.md": ".github/copilot-instructions.md",
    "config/compliance/cui-ai-policy.v1.json": "config/compliance/cui-ai-policy.v1.json",
}

AGENT_GLOBS = (".cursor/agents/*.md", ".claude/agents/*.md")


def policy_hash(policy_file: Path) -> str:
    return hashlib.sha256(policy_file.read_bytes()).hexdigest()


def bind_agent_files(root: Path) -> list[str]:
    changed: list[str] = []
    for pattern in AGENT_GLOBS:
        for path in sorted(root.glob(pattern)):
            text = path.read_text(encoding="utf-8")
            if MARKER in text:
                continue
            if text.startswith("---\n"):
                end = text.find("\n---\n", 4)
                if end >= 0:
                    insert_at = end + len("\n---\n")
                    text = text[:insert_at] + "\n" + BLOCK + text[insert_at:]
                else:
                    text = BLOCK + text
            else:
                text = BLOCK + text
            path.write_text(text, encoding="utf-8")
            changed.append(str(path.relative_to(root)))
    return changed


def verify(root: Path, canonical_policy: Path) -> list[str]:
    failures: list[str] = []
    if not canonical_policy.exists():
        failures.append(f"missing canonical policy: {canonical_policy}")
    elif policy_hash(canonical_policy) != POLICY_SHA256:
        failures.append("canonical policy hash mismatch")

    for target_rel in MANAGED_FILES:
        if not (root / target_rel).exists():
            failures.append(f"missing managed file: {target_rel}")

    for pattern in AGENT_GLOBS:
        for path in sorted(root.glob(pattern)):
            if MARKER not in path.read_text(encoding="utf-8"):
                failures.append(f"agent not bound: {path.relative_to(root)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, default=Path("AI_AGENT_CUI_RULES_OF_BEHAVIOR_JUL15_2026.md"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bind", action="store_true", help="prepend the policy block to existing Cursor/Claude agent files")
    args = parser.parse_args()

    root = args.root.resolve()
    policy = args.policy if args.policy.is_absolute() else root / args.policy

    if args.bind:
        for item in bind_agent_files(root):
            print(f"UPDATED: {item}")

    failures = verify(root, policy)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: CUI policy bindings verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
