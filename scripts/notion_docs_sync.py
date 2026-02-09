#!/usr/bin/env python3
"""
Mycosoft Documentation → Notion Sync System (Feb 08, 2026)

Comprehensive sync of ALL documentation across all Mycosoft repos to Notion.
- Scans all repos: MAS, WEBSITE, MINDEX, MycoBrain, NatureOS, Cursor Plans
- Auto-categorizes documents by topic
- Versions documents (never replaces - creates new dated versions)
- Tracks sync state to avoid re-uploading unchanged docs
- Converts markdown to proper Notion blocks
- Handles Notion API rate limits

Usage:
    python scripts/notion_docs_sync.py                  # Full sync all repos
    python scripts/notion_docs_sync.py --repo MAS       # Sync single repo
    python scripts/notion_docs_sync.py --dry-run        # Preview without uploading
    python scripts/notion_docs_sync.py --setup          # Interactive setup
    python scripts/notion_docs_sync.py --force          # Re-sync everything
"""

import os
import sys
import json
import hashlib
import argparse
import time
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Run: pip install requests")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────────────────

# All repo docs folders to scan
REPO_CONFIGS = {
    "MAS": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs",
        "description": "Multi-Agent System",
        "color": "blue",
    },
    "WEBSITE": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\docs",
        "description": "Mycosoft Website",
        "color": "green",
    },
    "MINDEX": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\docs",
        "description": "MINDEX Database & Vector Store",
        "color": "purple",
    },
    "MycoBrain": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\docs",
        "description": "MycoBrain Firmware",
        "color": "orange",
    },
    "NatureOS": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\NATUREOS\NatureOS\docs",
        "description": "NatureOS Platform",
        "color": "yellow",
    },
    "Cursor Plans": {
        "docs_path": r"C:\Users\admin2\.cursor\plans",
        "description": "Cursor AI Development Plans",
        "color": "gray",
    },
    "MAS-NLM": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\NLM\docs",
        "description": "Natural Language Memory",
        "color": "pink",
    },
    "MAS-TRN": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\trn\docs",
        "description": "MAS TRN Module",
        "color": "red",
    },
    "Mycorrhizae": {
        "docs_path": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\Mycorrhizae\docs",
        "description": "Mycorrhizae Network Protocol",
        "color": "brown",
    },
}

# Category detection patterns (order matters - first match wins)
CATEGORY_PATTERNS = [
    (r"(?i)(memory|mem0|mcp_memory|personaplex_memory)", "Memory"),
    (r"(?i)(voice|speech|tts|stt|personaplex|moshi)", "Voice & AI"),
    (r"(?i)(earth2|earth_2|simulation|sim_data)", "Simulation"),
    (r"(?i)(device|firmware|mycobrain|mushroom|sporebase|trufflebot|myconode|mycotenna|petraeus)", "Devices & Firmware"),
    (r"(?i)(deploy|docker|container|sandbox|pipeline|ci_cd|rebuild)", "Deployment"),
    (r"(?i)(vm_|proxmox|infrastructure|nas|backup|recovery|data_loss)", "Infrastructure"),
    (r"(?i)(api_|endpoint|route|catalog|swagger)", "API"),
    (r"(?i)(security|audit|rbac|encryption|auth)", "Security"),
    (r"(?i)(scientific|bio|dna|protein|mycelium|lab|experiment|crep)", "Scientific"),
    (r"(?i)(test|report|verification|browser_test)", "Testing"),
    (r"(?i)(integration|sync|bridge|connect|mindex_.*integration|n8n)", "Integration"),
    (r"(?i)(architecture|design|system_map|registry)", "Architecture"),
    (r"(?i)(plan|roadmap|phase|milestone|strategy)", "Planning"),
    (r"(?i)(search|mindex_query|rag|vector)", "Search & Index"),
    (r"(?i)(agent|orchestrator|workflow|autonomous)", "Agents & Orchestration"),
    (r"(?i)(natureos|nature_os|signal|telemetry)", "NatureOS"),
    (r"(?i)(changelog|upgrade|migration|update)", "Changelog"),
    (r"(?i)(drone|wifisense|sensor|iot)", "IoT & Sensors"),
    (r"(?i)(notion|document_management|doc_sync)", "Documentation"),
    (r"(?i)(ledger|blockchain|token|dao|nft|ip_)", "Blockchain & IP"),
    (r"(?i)(finance|sales|marketing|business)", "Business"),
    (r"(?i)(gpu|cuda|nvidia|performance|slow|wsl|vmmem)", "Performance"),
    (r"(?i)(setup|install|guide|quickstart|readme|getting_started)", "Setup & Guides"),
]

# Sync state file
SYNC_STATE_FILE = Path(__file__).parent.parent / "data" / "notion_sync_state.json"

# Notion API limits
NOTION_MAX_BLOCK_TEXT = 2000  # Max chars per rich_text element
NOTION_MAX_BLOCKS_PER_REQUEST = 100  # Max blocks per append
NOTION_RATE_LIMIT_DELAY = 0.35  # seconds between requests (3 req/sec max)


class NotionDocsSync:
    """Comprehensive multi-repo documentation sync to Notion."""

    def __init__(self, api_key: str, database_id: str, dry_run: bool = False):
        self.api_key = api_key
        self.database_id = database_id
        self.dry_run = dry_run
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.sync_state = self._load_sync_state()
        self.stats = {
            "scanned": 0,
            "new": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "repos": {},
        }

    # ─── Sync State Management ───────────────────────────────────────────────

    def _load_sync_state(self) -> Dict:
        """Load previous sync state from disk."""
        if SYNC_STATE_FILE.exists():
            try:
                with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"synced_docs": {}, "last_full_sync": None, "version": 1}

    def _save_sync_state(self):
        """Save sync state to disk."""
        SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.sync_state["last_full_sync"] = datetime.now(timezone.utc).isoformat()
        with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sync_state, f, indent=2, default=str)

    def _get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of file content."""
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    # ─── Document Discovery ──────────────────────────────────────────────────

    def discover_documents(self, repo_filter: Optional[str] = None) -> List[Dict]:
        """Discover all .md files across all repos."""
        all_docs = []

        for repo_name, config in REPO_CONFIGS.items():
            if repo_filter and repo_name.lower() != repo_filter.lower():
                continue

            docs_path = Path(config["docs_path"])
            if not docs_path.exists():
                print(f"  [SKIP] {repo_name}: docs folder not found at {docs_path}")
                continue

            # Find all .md files (recursively)
            md_files = sorted(docs_path.rglob("*.md"))
            count = len(md_files)
            self.stats["repos"][repo_name] = count
            print(f"  [{repo_name}] Found {count} documents in {docs_path}")

            for md_file in md_files:
                try:
                    relative_path = md_file.relative_to(docs_path)
                    file_stat = md_file.stat()
                    file_hash = self._get_file_hash(md_file)
                    file_name = md_file.stem
                    category = self._detect_category(file_name)
                    date_from_name = self._extract_date_from_name(file_name)

                    doc_info = {
                        "name": file_name,
                        "filename": md_file.name,
                        "repo": repo_name,
                        "repo_description": config["description"],
                        "repo_color": config["color"],
                        "category": category,
                        "relative_path": str(relative_path),
                        "absolute_path": str(md_file),
                        "size_bytes": file_stat.st_size,
                        "modified_time": datetime.fromtimestamp(
                            file_stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                        "content_hash": file_hash,
                        "date_from_name": date_from_name,
                        "is_plan": ".plan.md" in md_file.name.lower()
                        or repo_name == "Cursor Plans",
                        "sync_key": f"{repo_name}:{relative_path}",
                    }
                    all_docs.append(doc_info)
                    self.stats["scanned"] += 1
                except Exception as e:
                    print(f"    [ERROR] {md_file}: {e}")
                    self.stats["errors"] += 1

        return all_docs

    def _detect_category(self, filename: str) -> str:
        """Auto-detect document category from filename."""
        for pattern, category in CATEGORY_PATTERNS:
            if re.search(pattern, filename):
                return category
        return "General"

    def _extract_date_from_name(self, filename: str) -> Optional[str]:
        """Extract date from filename like MEMORY_SYSTEM_FEB05_2026."""
        # Pattern: MON DD YYYY or MON_DD_YYYY
        month_map = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
            "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
            "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
        }
        match = re.search(
            r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[_-]?(\d{2})[_-]?(\d{4})",
            filename.upper(),
        )
        if match:
            month = month_map.get(match.group(1), "01")
            day = match.group(2)
            year = match.group(3)
            return f"{year}-{month}-{day}"

        # Pattern: YYYY-MM-DD or YYYY_MM_DD
        match = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2})", filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

        return None

    # ─── Notion API ──────────────────────────────────────────────────────────

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited Notion API request."""
        time.sleep(NOTION_RATE_LIMIT_DELAY)
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "POST":
                resp = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PATCH":
                resp = requests.patch(url, headers=self.headers, json=data, timeout=30)
            elif method == "GET":
                resp = requests.get(url, headers=self.headers, timeout=30)
            else:
                return None

            if resp.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"    [RATE LIMIT] Waiting {retry_after}s...")
                time.sleep(retry_after)
                return self._api_request(method, endpoint, data)

            if resp.status_code >= 400:
                error_body = resp.text[:500]
                print(f"    [API ERROR] {resp.status_code}: {error_body}")
                return None

            return resp.json()
        except requests.exceptions.Timeout:
            print(f"    [TIMEOUT] {endpoint}")
            return None
        except Exception as e:
            print(f"    [ERROR] {endpoint}: {e}")
            return None

    def health_check(self) -> bool:
        """Verify Notion API connectivity."""
        result = self._api_request("GET", "/users/me")
        if result and "id" in result:
            bot_name = result.get("name", "Unknown")
            print(f"  Notion API connected as: {bot_name}")
            return True
        print("  ERROR: Notion API health check failed")
        return False

    def ensure_database_properties(self):
        """Ensure the Notion database has all required properties."""
        if self.dry_run:
            return

        properties_to_add = {
            "Repo": {"select": {}},
            "Category": {"select": {}},
            "File Path": {"rich_text": {}},
            "Source Type": {"select": {}},
            "Sync Date": {"date": {}},
            "File Modified": {"date": {}},
            "Content Hash": {"rich_text": {}},
            "File Size": {"number": {"format": "number"}},
            "Document Date": {"rich_text": {}},
        }

        print("  Ensuring database properties exist...")
        result = self._api_request("PATCH", f"/databases/{self.database_id}", {
            "properties": properties_to_add,
        })
        if result:
            print("  Database properties configured.")
        else:
            print("  WARNING: Could not update database properties. They may need manual creation.")

    # ─── Markdown → Notion Blocks ────────────────────────────────────────────

    def _chunk_text(self, text: str, max_len: int = NOTION_MAX_BLOCK_TEXT) -> List[str]:
        """Split text into chunks respecting the Notion 2000-char limit."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            # Find a good break point (newline, space)
            break_at = text.rfind("\n", 0, max_len)
            if break_at == -1 or break_at < max_len // 2:
                break_at = text.rfind(" ", 0, max_len)
            if break_at == -1 or break_at < max_len // 2:
                break_at = max_len
            chunks.append(text[:break_at])
            text = text[break_at:].lstrip("\n")

        return chunks

    def _make_rich_text(self, text: str) -> List[Dict]:
        """Create rich_text array, chunking if needed."""
        chunks = self._chunk_text(text)
        return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]

    def markdown_to_blocks(self, markdown: str) -> List[Dict]:
        """Convert markdown to Notion blocks with proper handling."""
        blocks = []
        lines = markdown.split("\n")
        i = 0
        current_paragraph = []
        in_code_block = False
        code_lines = []
        code_lang = "plain text"

        def flush_paragraph():
            nonlocal current_paragraph
            if current_paragraph:
                text = "\n".join(current_paragraph)
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
                current_paragraph = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Code block handling
            if stripped.startswith("```"):
                if in_code_block:
                    # End code block
                    in_code_block = False
                    code_content = "\n".join(code_lines)
                    for chunk in self._chunk_text(code_content):
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "language": normalize_code_language(code_lang),
                                "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            },
                        })
                    code_lines = []
                else:
                    # Start code block
                    flush_paragraph()
                    in_code_block = True
                    lang = stripped[3:].strip().lower()
                    code_lang = lang if lang else "plain text"
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Headings
            if stripped.startswith("### "):
                flush_paragraph()
                text = stripped[4:]
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            elif stripped.startswith("## "):
                flush_paragraph()
                text = stripped[3:]
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            elif stripped.startswith("# "):
                flush_paragraph()
                text = stripped[2:]
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            # Divider
            elif stripped in ("---", "***", "___"):
                flush_paragraph()
                blocks.append({"object": "block", "type": "divider", "divider": {}})
            # Bullet list
            elif stripped.startswith("- ") or stripped.startswith("* "):
                flush_paragraph()
                text = stripped[2:]
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            # Numbered list
            elif re.match(r"^\d+\.\s", stripped):
                flush_paragraph()
                text = re.sub(r"^\d+\.\s", "", stripped)
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            # Blockquote
            elif stripped.startswith("> "):
                flush_paragraph()
                text = stripped[2:]
                for chunk in self._chunk_text(text):
                    blocks.append({
                        "object": "block",
                        "type": "quote",
                        "quote": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        },
                    })
            # Table row (simplified - as paragraph)
            elif stripped.startswith("|") and stripped.endswith("|"):
                current_paragraph.append(stripped)
            # Empty line
            elif stripped == "":
                flush_paragraph()
            # Regular text
            else:
                current_paragraph.append(line)

            i += 1

        # Flush remaining
        if in_code_block and code_lines:
            code_content = "\n".join(code_lines)
            for chunk in self._chunk_text(code_content):
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": "plain text",
                        "rich_text": [{"type": "text", "text": {"content": chunk}}],
                    },
                })
        flush_paragraph()

        # Notion limit: max 100 children per request
        return blocks[:NOTION_MAX_BLOCKS_PER_REQUEST]

    # ─── Create/Update Pages ─────────────────────────────────────────────────

    def create_doc_page(self, doc: Dict) -> Optional[str]:
        """Create a new Notion page for a document."""
        # Read file content
        try:
            content = Path(doc["absolute_path"]).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"    [ERROR] Could not read {doc['absolute_path']}: {e}")
            return None

        now = datetime.now(timezone.utc).isoformat()
        source_type = "Plan" if doc["is_plan"] else "Documentation"

        # Build title with version date
        title = doc["name"]
        if doc["date_from_name"]:
            title_display = f"{doc['name']}"
        else:
            title_display = f"{doc['name']} (synced {datetime.now().strftime('%Y-%m-%d')})"

        # Properties
        properties = {
            "Name": {"title": [{"text": {"content": title_display}}]},
            "Repo": {"select": {"name": doc["repo"]}},
            "Category": {"select": {"name": doc["category"]}},
            "File Path": {"rich_text": [{"text": {"content": doc["relative_path"][:2000]}}]},
            "Source Type": {"select": {"name": source_type}},
            "Sync Date": {"date": {"start": now}},
            "Content Hash": {"rich_text": [{"text": {"content": doc["content_hash"]}}]},
            "File Size": {"number": doc["size_bytes"]},
        }

        if doc["modified_time"]:
            properties["File Modified"] = {"date": {"start": doc["modified_time"]}}

        if doc["date_from_name"]:
            properties["Document Date"] = {
                "rich_text": [{"text": {"content": doc["date_from_name"]}}]
            }

        # Convert markdown to Notion blocks
        blocks = self.markdown_to_blocks(content)

        # Prepend metadata block
        meta_block = {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "📄"},
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": (
                                f"Repo: {doc['repo']} | "
                                f"Category: {doc['category']} | "
                                f"Path: {doc['relative_path']} | "
                                f"Hash: {doc['content_hash']}"
                            )
                        },
                    }
                ],
            },
        }
        blocks.insert(0, meta_block)
        blocks = blocks[:NOTION_MAX_BLOCKS_PER_REQUEST]

        if self.dry_run:
            print(f"    [DRY RUN] Would create: {title_display} ({len(blocks)} blocks)")
            return "dry-run-id"

        # Create the page
        page_data = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": blocks,
        }

        result = self._api_request("POST", "/pages", page_data)
        if result and "id" in result:
            page_id = result["id"]
            print(f"    [CREATED] {title_display} -> {page_id}")

            # If content exceeds 100 blocks, append remaining in batches
            if len(self.markdown_to_blocks(content)) > NOTION_MAX_BLOCKS_PER_REQUEST - 1:
                remaining = self.markdown_to_blocks(content)[NOTION_MAX_BLOCKS_PER_REQUEST - 1:]
                for batch_start in range(0, len(remaining), NOTION_MAX_BLOCKS_PER_REQUEST):
                    batch = remaining[batch_start : batch_start + NOTION_MAX_BLOCKS_PER_REQUEST]
                    self._api_request("PATCH", f"/blocks/{page_id}/children", {"children": batch})

            return page_id
        return None

    # ─── Sync Logic ──────────────────────────────────────────────────────────

    def should_sync(self, doc: Dict, force: bool = False) -> Tuple[bool, str]:
        """Determine if a document needs syncing."""
        if force:
            return True, "forced"

        sync_key = doc["sync_key"]
        prev = self.sync_state.get("synced_docs", {}).get(sync_key)

        if not prev:
            return True, "new"

        if prev.get("content_hash") != doc["content_hash"]:
            return True, "changed"

        return False, "unchanged"

    def sync_all(
        self,
        repo_filter: Optional[str] = None,
        force: bool = False,
    ):
        """Run the full sync process."""
        print("=" * 70)
        print("  MYCOSOFT DOCUMENTATION -> NOTION SYNC")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.dry_run:
            print("  MODE: DRY RUN (no changes will be made)")
        print("=" * 70)

        # Health check
        if not self.dry_run:
            print("\n[1/4] Checking Notion API...")
            if not self.health_check():
                print("ABORTED: Cannot connect to Notion API.")
                return

            print("\n[2/4] Configuring database properties...")
            self.ensure_database_properties()
        else:
            print("\n[1/4] Skipping API check (dry run)")
            print("[2/4] Skipping database config (dry run)")

        # Discover documents
        print(f"\n[3/4] Discovering documents across repos...")
        docs = self.discover_documents(repo_filter)
        print(f"\n  Total documents found: {len(docs)}")

        # Sync
        print(f"\n[4/4] Syncing to Notion...")
        to_sync = []
        for doc in docs:
            needs_sync, reason = self.should_sync(doc, force)
            if needs_sync:
                to_sync.append((doc, reason))
            else:
                self.stats["skipped"] += 1

        if not to_sync:
            print("  No documents need syncing (all up to date).")
        else:
            print(f"  Documents to sync: {len(to_sync)}")
            print(f"  Skipped (unchanged): {self.stats['skipped']}")
            print()

            for idx, (doc, reason) in enumerate(to_sync, 1):
                prefix = f"  [{idx}/{len(to_sync)}]"
                reason_tag = "[NEW]" if reason == "new" else "[UPDATED]" if reason == "changed" else f"[{reason.upper()}]"
                print(f"{prefix} {reason_tag} {doc['repo']}/{doc['filename']}")

                page_id = self.create_doc_page(doc)
                if page_id:
                    if reason == "new":
                        self.stats["new"] += 1
                    else:
                        self.stats["updated"] += 1

                    # Update sync state
                    self.sync_state.setdefault("synced_docs", {})[doc["sync_key"]] = {
                        "content_hash": doc["content_hash"],
                        "notion_page_id": page_id,
                        "synced_at": datetime.now(timezone.utc).isoformat(),
                        "repo": doc["repo"],
                        "filename": doc["filename"],
                        "reason": reason,
                    }
                else:
                    self.stats["errors"] += 1

        # Save state
        if not self.dry_run:
            self._save_sync_state()

        # Print summary
        print("\n" + "=" * 70)
        print("  SYNC COMPLETE")
        print("=" * 70)
        print(f"  Scanned:  {self.stats['scanned']}")
        print(f"  New:      {self.stats['new']}")
        print(f"  Updated:  {self.stats['updated']}")
        print(f"  Skipped:  {self.stats['skipped']}")
        print(f"  Errors:   {self.stats['errors']}")
        print(f"\n  Repos:")
        for repo, count in self.stats["repos"].items():
            print(f"    {repo}: {count} docs")
        print("=" * 70)

    def sync_single_file(self, file_path: str):
        """Sync a single file to Notion (used by watcher)."""
        fp = Path(file_path)
        if not fp.exists() or not fp.suffix == ".md":
            return False

        # Determine which repo this belongs to
        repo_name = None
        docs_path = None
        for name, config in REPO_CONFIGS.items():
            config_path = Path(config["docs_path"])
            try:
                fp.relative_to(config_path)
                repo_name = name
                docs_path = config_path
                break
            except ValueError:
                continue

        if not repo_name:
            print(f"  [SKIP] {file_path} not in any known docs folder")
            return False

        config = REPO_CONFIGS[repo_name]
        file_hash = self._get_file_hash(fp)
        file_stat = fp.stat()
        relative_path = str(fp.relative_to(docs_path))
        file_name = fp.stem

        doc = {
            "name": file_name,
            "filename": fp.name,
            "repo": repo_name,
            "repo_description": config["description"],
            "repo_color": config["color"],
            "category": self._detect_category(file_name),
            "relative_path": relative_path,
            "absolute_path": str(fp),
            "size_bytes": file_stat.st_size,
            "modified_time": datetime.fromtimestamp(
                file_stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "content_hash": file_hash,
            "date_from_name": self._extract_date_from_name(file_name),
            "is_plan": ".plan.md" in fp.name.lower() or repo_name == "Cursor Plans",
            "sync_key": f"{repo_name}:{relative_path}",
        }

        needs_sync, reason = self.should_sync(doc)
        if not needs_sync:
            return False

        print(f"  [AUTO-SYNC] [{reason.upper()}] {repo_name}/{fp.name}")
        page_id = self.create_doc_page(doc)
        if page_id:
            self.sync_state.setdefault("synced_docs", {})[doc["sync_key"]] = {
                "content_hash": doc["content_hash"],
                "notion_page_id": page_id,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "repo": doc["repo"],
                "filename": doc["filename"],
                "reason": reason,
            }
            self._save_sync_state()
            return True
        return False


# Mapping from common markdown code fence languages to Notion API language names
LANG_ALIASES = {
    "cpp": "c++",
    "c++": "c++",
    "csharp": "c#",
    "cs": "c#",
    "c#": "c#",
    "fsharp": "f#",
    "fs": "f#",
    "f#": "f#",
    "vbnet": "vb.net",
    "vb": "vb.net",
    "vb.net": "vb.net",
    "objc": "objective-c",
    "objective-c": "objective-c",
    "objectivec": "objective-c",
    "sh": "bash",
    "zsh": "bash",
    "shell": "bash",
    "bat": "bash",
    "cmd": "bash",
    "ps1": "powershell",
    "ps": "powershell",
    "posh": "powershell",
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "yml": "yaml",
    "toml": "yaml",
    "ini": "yaml",
    "cfg": "yaml",
    "conf": "yaml",
    "dockerfile": "docker",
    "env": "plain text",
    "txt": "plain text",
    "text": "plain text",
    "log": "plain text",
    "csv": "plain text",
    "md": "markdown",
    "mdx": "markdown",
    "htm": "html",
    "svelte": "html",
    "vue": "html",
    "jsonc": "json",
    "json5": "json",
    "rs": "rust",
    "rb": "ruby",
    "kt": "kotlin",
    "kts": "kotlin",
    "asm": "assembly",
    "s": "assembly",
    "wasm": "webassembly",
    "proto": "protobuf",
    "graphql": "graphql",
    "gql": "graphql",
    "tex": "latex",
    "m": "matlab",
    "mm": "objective-c",
    "pl": "perl",
    "ex": "elixir",
    "exs": "elixir",
    "erl": "erlang",
    "hs": "haskell",
    "ml": "ocaml",
    "clj": "clojure",
    "rkt": "scheme",
    "scm": "scheme",
    "jl": "julia",
    "r": "r",
    "pas": "pascal",
    "nim": "plain text",
    "zig": "plain text",
    "v": "verilog",
    "sv": "verilog",
    "vhd": "vhdl",
    "glsl": "glsl",
    "hlsl": "glsl",
    "sol": "plain text",
    "tf": "plain text",
    "hcl": "plain text",
    "prisma": "plain text",
    "plantuml": "plain text",
    "output": "plain text",
    "console": "bash",
    "terminal": "bash",
}

# Valid Notion API code language values (as of 2026-02)
NOTION_LANGUAGES = {
    "abap", "abc", "agda", "arduino", "ascii art", "assembly",
    "bash", "basic", "bnf",
    "c", "c#", "c++", "clojure", "coffeescript", "coq", "css",
    "dart", "dhall", "diff", "docker",
    "ebnf", "elixir", "elm", "erlang",
    "f#", "flow", "fortran",
    "gherkin", "glsl", "go", "graphql", "groovy",
    "haskell", "html",
    "idris",
    "java", "javascript", "json", "julia",
    "kotlin",
    "latex", "less", "lisp", "livescript", "llvm ir", "lua",
    "makefile", "markdown", "markup", "matlab", "mathematica", "mermaid",
    "nix",
    "objective-c", "ocaml",
    "pascal", "perl", "php", "plain text", "powershell", "prolog", "protobuf", "purescript", "python",
    "r", "racket", "reason", "ruby", "rust",
    "sass", "scala", "scheme", "scss", "shell", "smalltalk", "solidity", "sql", "swift",
    "toml", "typescript",
    "vb.net", "verilog", "vhdl", "visual basic",
    "webassembly", "wasm",
    "xml",
    "yaml",
    "zig",
    "java/c/c++/c#",
}


def normalize_code_language(lang: str) -> str:
    """Normalize a markdown code fence language to a valid Notion API language."""
    lang = lang.strip().lower()
    if not lang:
        return "plain text"
    # Check alias map first
    if lang in LANG_ALIASES:
        return LANG_ALIASES[lang]
    # Check if already valid
    if lang in NOTION_LANGUAGES:
        return lang
    # Fallback
    return "plain text"


def setup_interactive():
    """Interactive setup wizard."""
    print("=" * 60)
    print("  MYCOSOFT NOTION SYNC - SETUP WIZARD")
    print("=" * 60)
    print()
    print("This will configure Notion integration for documentation sync.")
    print()
    print("Step 1: Create a Notion Integration")
    print("  1. Go to https://www.notion.so/my-integrations")
    print("  2. Click 'New integration'")
    print("  3. Name: 'Mycosoft Docs Sync'")
    print("  4. Select your workspace")
    print("  5. Enable: Read, Update, Insert content")
    print("  6. Copy the 'Internal Integration Secret'")
    print()

    api_key = input("Paste your Notion API key (secret_...): ").strip()
    if not api_key.startswith("secret_"):
        print("WARNING: Key should start with 'secret_'. Continuing anyway...")

    print()
    print("Step 2: Create a Notion Database")
    print("  1. In Notion, create a new full-page Database")
    print("  2. Name: 'Mycosoft Documentation'")
    print("  3. Share it with your 'Mycosoft Docs Sync' integration")
    print("  4. Copy the Database ID from the URL")
    print("     URL: https://notion.so/workspace/<DATABASE_ID>?v=...")
    print()

    database_id = input("Paste your Database ID: ").strip()
    # Clean up - remove any URL parts
    if "notion.so" in database_id:
        # Extract ID from URL
        parts = database_id.split("/")
        for part in reversed(parts):
            clean = part.split("?")[0]
            if len(clean) >= 32:
                database_id = clean
                break

    print()
    print("Step 3: Saving configuration...")

    # Save to .env
    env_file = Path(__file__).parent.parent / ".env"
    env_content = ""
    if env_file.exists():
        env_content = env_file.read_text(encoding="utf-8")

    # Update or add keys
    if "NOTION_API_KEY=" in env_content:
        lines = env_content.split("\n")
        lines = [
            f"NOTION_API_KEY={api_key}" if l.startswith("NOTION_API_KEY=") else l
            for l in lines
        ]
        env_content = "\n".join(lines)
    else:
        env_content += f"\nNOTION_API_KEY={api_key}\n"

    if "NOTION_DATABASE_ID=" in env_content:
        lines = env_content.split("\n")
        lines = [
            f"NOTION_DATABASE_ID={database_id}" if l.startswith("NOTION_DATABASE_ID=") else l
            for l in lines
        ]
        env_content = "\n".join(lines)
    else:
        env_content += f"NOTION_DATABASE_ID={database_id}\n"

    env_file.write_text(env_content, encoding="utf-8")
    print(f"  Saved to {env_file}")

    # Also set as environment variables for current session
    os.environ["NOTION_API_KEY"] = api_key
    os.environ["NOTION_DATABASE_ID"] = database_id

    # Set as persistent user-level env vars
    print()
    print("Step 4: Setting persistent environment variables...")
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-Command",
             f'[Environment]::SetEnvironmentVariable("NOTION_API_KEY", "{api_key}", "User")'],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["powershell", "-Command",
             f'[Environment]::SetEnvironmentVariable("NOTION_DATABASE_ID", "{database_id}", "User")'],
            check=True, capture_output=True,
        )
        print("  Environment variables set at User level.")
    except Exception as e:
        print(f"  Could not set persistent env vars: {e}")
        print(f"  Please set manually:")
        print(f'    $env:NOTION_API_KEY = "{api_key}"')
        print(f'    $env:NOTION_DATABASE_ID = "{database_id}"')

    # Test connection
    print()
    print("Step 5: Testing connection...")
    syncer = NotionDocsSync(api_key, database_id)
    if syncer.health_check():
        print("  SUCCESS! Notion API is connected.")
        print()
        print("You can now run:")
        print("  python scripts/notion_docs_sync.py            # Full sync")
        print("  python scripts/notion_docs_sync.py --dry-run  # Preview")
        print("  python scripts/notion_docs_watcher.py         # Auto-watch")
    else:
        print("  FAILED. Please verify your API key and that the integration")
        print("  has been shared with the database.")

    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Mycosoft Documentation -> Notion Sync"
    )
    parser.add_argument("--setup", action="store_true", help="Run interactive setup")
    parser.add_argument("--repo", type=str, help="Sync only a specific repo (e.g., MAS, WEBSITE)")
    parser.add_argument("--dry-run", action="store_true", help="Preview sync without making changes")
    parser.add_argument("--force", action="store_true", help="Re-sync all documents even if unchanged")
    parser.add_argument("--file", type=str, help="Sync a single file")

    args = parser.parse_args()

    if args.setup:
        setup_interactive()
        return

    # Load env from .env file if present
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value

    api_key = os.environ.get("NOTION_API_KEY", "")
    database_id = os.environ.get("NOTION_DATABASE_ID", "")

    if (not api_key or not database_id) and not args.dry_run:
        print("ERROR: NOTION_API_KEY and NOTION_DATABASE_ID must be set.")
        print("Run: python scripts/notion_docs_sync.py --setup")
        print("Or use --dry-run to preview without credentials.")
        sys.exit(1)

    syncer = NotionDocsSync(
        api_key or "dry-run",
        database_id or "dry-run",
        dry_run=args.dry_run,
    )

    if args.file:
        syncer.sync_single_file(args.file)
    else:
        syncer.sync_all(repo_filter=args.repo, force=args.force)


if __name__ == "__main__":
    main()
