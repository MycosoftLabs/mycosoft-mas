"""
MYCA File Manager — Manages files on VM 191.

Provides MYCA with awareness of her own filesystem:
- Index and search files by type, category, tags
- Track file changes and modifications
- Organize workspace directories
- Back up important files
- Clean up temporary files

VM 191 Directory Layout:
    /home/mycosoft/
    ├── repos/                  # Git repositories
    │   ├── mycosoft-mas/       # Main MAS repo
    │   ├── mycosoft-website/   # Website repo
    │   └── mindex/             # MINDEX repo
    ├── documents/              # Personal docs, notes, plans
    ├── downloads/              # Downloaded files
    └── .config/                # App configs (Claude, Cursor, etc.)
    /opt/myca/
    ├── logs/                   # MYCA OS logs
    ├── data/                   # Persistent data
    ├── backups/                # Automated backups
    └── .env                    # Environment variables

Date: 2026-03-04
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("myca.os.files")


@dataclass
class FileEntry:
    """A tracked file in MYCA's filesystem."""

    path: str
    file_type: str = "unknown"  # document, code, config, media, data
    category: str = "uncategorized"
    description: str = ""
    size_bytes: int = 0
    checksum: str = ""
    tags: list = field(default_factory=list)
    last_modified: Optional[datetime] = None


# File type classification by extension
EXTENSION_TYPES = {
    # Code
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".go": "code",
    ".rs": "code",
    ".java": "code",
    ".rb": "code",
    ".sh": "code",
    ".sql": "code",
    ".html": "code",
    ".css": "code",
    ".vue": "code",
    # Config
    ".yaml": "config",
    ".yml": "config",
    ".json": "config",
    ".toml": "config",
    ".ini": "config",
    ".env": "config",
    ".conf": "config",
    ".cfg": "config",
    # Document
    ".md": "document",
    ".txt": "document",
    ".pdf": "document",
    ".doc": "document",
    ".docx": "document",
    ".rst": "document",
    # Data
    ".csv": "data",
    ".jsonl": "data",
    ".parquet": "data",
    ".sqlite": "data",
    ".db": "data",
    ".xlsx": "data",
    # Media
    ".png": "media",
    ".jpg": "media",
    ".jpeg": "media",
    ".gif": "media",
    ".svg": "media",
    ".mp3": "media",
    ".mp4": "media",
    ".wav": "media",
}


class FileManager:
    """MYCA's file management system."""

    # Directories MYCA owns and manages
    MANAGED_DIRS = [
        "/home/mycosoft/repos",
        "/home/mycosoft/documents",
        "/home/mycosoft/downloads",
        "/opt/myca",
    ]

    # Directories to never touch
    PROTECTED_DIRS = [
        "/etc",
        "/usr",
        "/var",
        "/boot",
        "/root",
    ]

    def __init__(self, os_ref):
        self._os = os_ref
        self._index: dict[str, FileEntry] = {}

    async def initialize(self):
        """Load file index from database."""
        try:
            bridge = self._os.mindex_bridge
            if bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM myca_files ORDER BY last_modified DESC")
                    for row in rows:
                        self._index[row["file_path"]] = FileEntry(
                            path=row["file_path"],
                            file_type=row.get("file_type", "unknown"),
                            category=row.get("category", ""),
                            description=row.get("description", ""),
                            size_bytes=row.get("size_bytes", 0),
                            checksum=row.get("checksum", ""),
                            tags=row.get("tags", []),
                            last_modified=row.get("last_modified"),
                        )
                logger.info(f"Loaded {len(self._index)} indexed files")
        except Exception as e:
            logger.warning(f"Could not load file index: {e}")

    async def scan(self, directory: str = None, depth: int = 3) -> int:
        """Scan a directory and update the index. Returns count of new files found."""
        dirs_to_scan = [directory] if directory else self.MANAGED_DIRS
        new_count = 0

        for scan_dir in dirs_to_scan:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                continue

            for root, dirs, files in os.walk(scan_path):
                # Depth limit
                rel_depth = str(root).count(os.sep) - str(scan_path).count(os.sep)
                if rel_depth >= depth:
                    dirs.clear()
                    continue

                # Skip hidden directories and common noise
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")
                ]

                for fname in files:
                    fpath = os.path.join(root, fname)
                    if fpath not in self._index:
                        entry = self._build_entry(fpath)
                        if entry:
                            self._index[fpath] = entry
                            new_count += 1

        if new_count > 0:
            logger.info(f"File scan found {new_count} new files")
            await self._persist_index()

        return new_count

    async def search(
        self, query: str = None, file_type: str = None, category: str = None, tags: list = None
    ) -> list[FileEntry]:
        """Search the file index."""
        results = list(self._index.values())

        if file_type:
            results = [f for f in results if f.file_type == file_type]
        if category:
            results = [f for f in results if f.category == category]
        if tags:
            results = [f for f in results if any(t in f.tags for t in tags)]
        if query:
            query_lower = query.lower()
            results = [
                f
                for f in results
                if query_lower in f.path.lower()
                or query_lower in f.description.lower()
                or query_lower in " ".join(f.tags).lower()
            ]

        return results

    async def organize(self, source_dir: str, rules: dict = None) -> dict:
        """Organize files in a directory by type/category."""
        rules = rules or {
            "code": "code",
            "document": "documents",
            "config": "config",
            "data": "data",
            "media": "media",
        }
        moved = {}
        source = Path(source_dir)

        for fpath, entry in list(self._index.items()):
            if not fpath.startswith(str(source)):
                continue
            dest_subdir = rules.get(entry.file_type)
            if dest_subdir:
                dest = source / dest_subdir / Path(fpath).name
                if str(dest) != fpath and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    Path(fpath).rename(dest)
                    moved[fpath] = str(dest)
                    # Update index
                    del self._index[fpath]
                    entry.path = str(dest)
                    self._index[str(dest)] = entry

        if moved:
            await self._persist_index()
            logger.info(f"Organized {len(moved)} files in {source_dir}")

        return moved

    async def cleanup_temp(self) -> int:
        """Clean up temporary and unnecessary files."""
        cleaned = 0
        temp_patterns = ["*.tmp", "*.pyc", "*.log.old", ".DS_Store", "Thumbs.db"]

        for scan_dir in self.MANAGED_DIRS:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                continue

            for pattern in temp_patterns:
                for f in scan_path.rglob(pattern):
                    try:
                        f.unlink()
                        if str(f) in self._index:
                            del self._index[str(f)]
                        cleaned += 1
                    except Exception:
                        pass

        if cleaned:
            logger.info(f"Cleaned up {cleaned} temporary files")
        return cleaned

    async def backup(self, paths: list = None, dest: str = "/opt/myca/backups") -> str:
        """Back up specified paths to the backup directory."""
        import tarfile
        from datetime import datetime

        paths = paths or ["/opt/myca/.env", "/opt/myca/data"]
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = dest_path / f"myca_backup_{timestamp}.tar.gz"

        with tarfile.open(backup_file, "w:gz") as tar:
            for p in paths:
                if Path(p).exists():
                    tar.add(p, arcname=Path(p).name)

        logger.info(f"Backup created: {backup_file}")
        return str(backup_file)

    def stats(self) -> dict:
        """Get file index statistics."""
        type_counts = {}
        total_size = 0
        for entry in self._index.values():
            type_counts[entry.file_type] = type_counts.get(entry.file_type, 0) + 1
            total_size += entry.size_bytes

        return {
            "total_files": len(self._index),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": type_counts,
        }

    # ── Helpers ──────────────────────────────────────────────────

    def _build_entry(self, fpath: str) -> Optional[FileEntry]:
        """Build a FileEntry from a file path."""
        try:
            p = Path(fpath)
            if not p.is_file():
                return None

            stat = p.stat()
            ext = p.suffix.lower()

            return FileEntry(
                path=fpath,
                file_type=EXTENSION_TYPES.get(ext, "unknown"),
                category=self._categorize(fpath),
                size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            )
        except Exception:
            return None

    def _categorize(self, fpath: str) -> str:
        """Categorize a file by its path."""
        fpath_lower = fpath.lower()
        if "/repos/" in fpath_lower:
            return "repository"
        elif "/documents/" in fpath_lower:
            return "personal"
        elif "/opt/myca/" in fpath_lower:
            return "system"
        elif "/downloads/" in fpath_lower:
            return "downloads"
        elif "/.config/" in fpath_lower:
            return "configuration"
        return "other"

    async def _persist_index(self):
        """Persist the file index to the database."""
        try:
            bridge = self._os.mindex_bridge
            if bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    for entry in self._index.values():
                        await conn.execute(
                            """INSERT INTO myca_files
                               (file_path, file_type, category, description, size_bytes, checksum, tags, last_modified)
                               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                               ON CONFLICT (file_path) DO UPDATE SET
                                   file_type = EXCLUDED.file_type,
                                   size_bytes = EXCLUDED.size_bytes,
                                   last_modified = EXCLUDED.last_modified""",
                            entry.path,
                            entry.file_type,
                            entry.category,
                            entry.description,
                            entry.size_bytes,
                            entry.checksum,
                            entry.tags,
                            entry.last_modified,
                        )
        except Exception as e:
            logger.warning(f"File index persist failed: {e}")
