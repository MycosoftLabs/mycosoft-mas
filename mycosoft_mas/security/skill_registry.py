"""
Skill Registry - Allow-list / deny-list registry for approved community skills.

Stores skill metadata and audit status in a JSON file. Provides methods to
register, approve, deny, and audit skills (integrating with SkillScanner).
Thread-safe with file locking.

All imports are from the Python standard library.

Created: February 9, 2026
"""

import hashlib
import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from .skill_scanner import ScanResult, SkillScanner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default registry path
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DEFAULT_REGISTRY_PATH = _DEFAULT_REGISTRY_DIR / "skill_registry.json"

# ---------------------------------------------------------------------------
# Skill entry dataclass
# ---------------------------------------------------------------------------


@dataclass
class SkillEntry:
    """A single skill record in the registry."""
    name: str
    version: str
    source_url: str
    purpose: str
    status: str                          # "allowed", "denied", "pending"
    last_audit_date: str                 # ISO-8601 UTC
    audit_notes: str
    sha256_hash: str
    registered_at: str = ""              # ISO-8601 UTC
    denied_reason: str = ""
    scan_findings_count: int = 0
    scan_risk_level: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillEntry":
        # Accept unknown keys gracefully (forward compat)
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


# ---------------------------------------------------------------------------
# Initial blocklist — seeded from ClawHub audit and known malicious skills
# ---------------------------------------------------------------------------

INITIAL_BLOCKLIST: List[Dict[str, str]] = [
    {
        "name": "cursor-shadow-workspace",
        "version": "*",
        "source_url": "https://github.com/clawhub-audit/cursor-shadow-workspace",
        "purpose": "Fake workspace manager — deploys Atomic Stealer (AMOS) payload",
        "denied_reason": (
            "ClawHub audit: Uses osascript to harvest macOS Keychain credentials, "
            "exfiltrates browser cookies and crypto wallet files via Telegram bot API. "
            "Contains obfuscated Base64 payload in setup.py install command override."
        ),
    },
    {
        "name": "auto-prerequisite-installer",
        "version": "*",
        "source_url": "https://github.com/clawhub-audit/auto-prereq-install",
        "purpose": "Fake dependency auto-installer — downloads and executes remote shell script",
        "denied_reason": (
            "ClawHub audit: curl | bash pattern downloading from attacker C2 domain. "
            "Installs persistent LaunchAgent on macOS and cron job on Linux for "
            "recurring credential exfiltration."
        ),
    },
    {
        "name": "code-assistant-plus",
        "version": "*",
        "source_url": "https://github.com/clawhub-audit/code-assistant-plus",
        "purpose": "Fake code assistant — reverse shell and env exfiltration",
        "denied_reason": (
            "ClawHub audit: Spawns reverse shell via socket.connect + subprocess.Popen. "
            "Harvests all environment variables (including API keys, tokens, secrets) "
            "and POSTs them to attacker-controlled Discord webhook."
        ),
    },
    {
        "name": "smart-format-tool",
        "version": "*",
        "source_url": "https://github.com/clawhub-audit/smart-format-tool",
        "purpose": "Fake formatter — typosquats popular tools, contains credential stealer",
        "denied_reason": (
            "ClawHub audit: Reads ~/.ssh/id_rsa, browser Login Data SQLite databases, "
            "and cloud CLI credential files. Exfiltrates via DNS TXT record queries "
            "with hex-encoded data embedded in subdomain labels."
        ),
    },
    {
        "name": "gpu-benchmark-suite",
        "version": "*",
        "source_url": "https://github.com/clawhub-audit/gpu-benchmark",
        "purpose": "Fake GPU benchmark — cryptocurrency miner payload",
        "denied_reason": (
            "ClawHub audit: Downloads XMRig Monero miner binary disguised as "
            "libcuda_benchmark.so. Configures mining pool via encoded config, "
            "installs as systemd service for persistence."
        ),
    },
]

# ---------------------------------------------------------------------------
# Platform-portable file locking
# ---------------------------------------------------------------------------


class _FileLock:
    """
    Cross-platform advisory file lock.

    On Unix uses fcntl.flock; on Windows uses msvcrt.locking.
    Falls back to a threading lock if neither is available.
    """

    def __init__(self, lock_path: str) -> None:
        self._lock_path = lock_path
        self._thread_lock = threading.Lock()
        self._fd: Optional[int] = None

    @contextmanager
    def acquire(self) -> Generator[None, None, None]:
        self._thread_lock.acquire()
        try:
            # Create/open lockfile
            self._fd = os.open(
                self._lock_path,
                os.O_CREAT | os.O_RDWR,
            )
            if os.name == "nt":
                # Windows locking via msvcrt
                import msvcrt
                while True:
                    try:
                        msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
            else:
                # Unix locking via fcntl
                import fcntl
                fcntl.flock(self._fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    import msvcrt
                    try:
                        os.lseek(self._fd, 0, os.SEEK_SET)
                        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
                self._fd = None
        finally:
            self._thread_lock.release()


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------


class SkillRegistry:
    """
    Thread-safe registry of community skills with allow/deny-list management.

    Skills are persisted in a JSON file at ``data/skill_registry.json``.
    The registry integrates with :class:`SkillScanner` to automatically
    scan and audit skill directories before approval.
    """

    def __init__(
        self,
        registry_path: Optional[str] = None,
        scanner: Optional[SkillScanner] = None,
    ) -> None:
        self._path = Path(registry_path) if registry_path else _DEFAULT_REGISTRY_PATH
        self._lock = _FileLock(str(self._path) + ".lock")
        self._scanner = scanner or SkillScanner()

        # Ensure data directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize registry file if it does not exist
        if not self._path.exists():
            self._write_registry({"skills": {}, "blocklist": [], "metadata": {
                "created_at": _now_iso(),
                "last_modified": _now_iso(),
                "version": "1.0.0",
            }})
            logger.info("Created new skill registry at %s", self._path)

        # Ensure blocklist is seeded
        self._seed_blocklist()

        logger.info("SkillRegistry initialized: %s", self._path)

    # ------------------------------------------------------------------
    # Public API — registration
    # ------------------------------------------------------------------

    def register_skill(
        self,
        name: str,
        version: str,
        source_url: str,
        purpose: str,
        sha256_hash: str = "",
        audit_notes: str = "",
    ) -> SkillEntry:
        """
        Register a new skill as *pending*. It must be approved or denied
        after registration (preferably via :meth:`audit_skill`).

        Returns the created SkillEntry.
        """
        now = _now_iso()
        entry = SkillEntry(
            name=name,
            version=version,
            source_url=source_url,
            purpose=purpose,
            status="pending",
            last_audit_date=now,
            audit_notes=audit_notes or "Registered, awaiting audit.",
            sha256_hash=sha256_hash,
            registered_at=now,
        )

        # Check if skill is on the blocklist
        if self._is_blocklisted(name):
            entry.status = "denied"
            entry.denied_reason = "Matched blocklist entry."
            entry.audit_notes = "Auto-denied: skill name matches blocklist."
            logger.warning("Skill '%s' auto-denied (blocklist match)", name)

        with self._lock.acquire():
            data = self._read_registry()
            data["skills"][name] = entry.to_dict()
            data["metadata"]["last_modified"] = now
            self._write_registry(data)

        logger.info("Registered skill '%s' (status=%s)", name, entry.status)
        return entry

    def approve_skill(self, name: str, notes: str = "") -> Optional[SkillEntry]:
        """Set a skill's status to *allowed*."""
        return self._set_status(name, "allowed", notes)

    def deny_skill(self, name: str, reason: str = "") -> Optional[SkillEntry]:
        """Set a skill's status to *denied*."""
        entry = self._set_status(name, "denied", reason)
        if entry:
            entry.denied_reason = reason
            # Persist the denied_reason
            with self._lock.acquire():
                data = self._read_registry()
                if name in data["skills"]:
                    data["skills"][name]["denied_reason"] = reason
                    data["metadata"]["last_modified"] = _now_iso()
                    self._write_registry(data)
        return entry

    def is_allowed(self, name: str) -> bool:
        """Return True if the skill is registered and has status *allowed*."""
        with self._lock.acquire():
            data = self._read_registry()
        skill = data["skills"].get(name)
        return skill is not None and skill.get("status") == "allowed"

    def get_skill(self, name: str) -> Optional[SkillEntry]:
        """Retrieve a single skill entry by name."""
        with self._lock.acquire():
            data = self._read_registry()
        raw = data["skills"].get(name)
        if raw is None:
            return None
        return SkillEntry.from_dict(raw)

    def get_all(self) -> List[SkillEntry]:
        """Return all registered skills."""
        with self._lock.acquire():
            data = self._read_registry()
        return [SkillEntry.from_dict(v) for v in data["skills"].values()]

    def get_denied(self) -> List[SkillEntry]:
        """Return all denied skills."""
        return [s for s in self.get_all() if s.status == "denied"]

    def get_pending(self) -> List[SkillEntry]:
        """Return all pending skills awaiting audit."""
        return [s for s in self.get_all() if s.status == "pending"]

    def get_allowed(self) -> List[SkillEntry]:
        """Return all allowed skills."""
        return [s for s in self.get_all() if s.status == "allowed"]

    # ------------------------------------------------------------------
    # Audit integration
    # ------------------------------------------------------------------

    def audit_skill(
        self,
        name: str,
        skill_path: str,
        auto_approve: bool = False,
    ) -> Optional[ScanResult]:
        """
        Run :class:`SkillScanner` against *skill_path* and update the
        registry entry for *name*.

        If `auto_approve` is True and the scan passes, the skill is
        automatically set to *allowed*. Otherwise critical/high findings
        set it to *denied*, and medium/low to *pending*.

        Returns the ScanResult.
        """
        result = self._scanner.scan_skill(skill_path)
        now = _now_iso()

        with self._lock.acquire():
            data = self._read_registry()
            skill = data["skills"].get(name)
            if skill is None:
                logger.warning(
                    "audit_skill: '%s' not found in registry; register first.", name
                )
                return result

            skill["last_audit_date"] = now
            skill["sha256_hash"] = result.sha256_hash
            skill["scan_findings_count"] = len(result.findings)
            skill["scan_risk_level"] = result.risk_level

            if result.passed:
                if auto_approve:
                    skill["status"] = "allowed"
                    skill["audit_notes"] = (
                        f"Auto-approved after clean scan ({result.scanned_files} files, "
                        f"risk={result.risk_level})."
                    )
                else:
                    skill["status"] = "pending"
                    skill["audit_notes"] = (
                        f"Scan passed ({result.scanned_files} files, "
                        f"risk={result.risk_level}). Manual approval required."
                    )
            else:
                # Critical or high findings → auto-deny
                critical = sum(1 for f in result.findings if f.severity == "critical")
                high = sum(1 for f in result.findings if f.severity == "high")
                if critical > 0 or high > 0:
                    skill["status"] = "denied"
                    findings_summary = "; ".join(
                        f.description for f in result.findings
                        if f.severity in ("critical", "high")
                    )[:500]
                    skill["audit_notes"] = (
                        f"Auto-denied: {critical} critical, {high} high findings. "
                        f"Summary: {findings_summary}"
                    )
                    skill["denied_reason"] = skill["audit_notes"]
                else:
                    skill["status"] = "pending"
                    skill["audit_notes"] = (
                        f"Scan flagged {len(result.findings)} medium/low findings. "
                        f"Manual review required."
                    )

            data["metadata"]["last_modified"] = now
            self._write_registry(data)

        logger.info(
            "Audited skill '%s': risk=%s, findings=%d, new_status=%s",
            name, result.risk_level, len(result.findings),
            skill["status"],
        )
        return result

    # ------------------------------------------------------------------
    # Blocklist management
    # ------------------------------------------------------------------

    def load_blocklist(self) -> List[Dict[str, str]]:
        """
        Read the deny-list of known malicious skills from the registry file.

        Returns a list of blocklist entries, each containing: name, version,
        source_url, purpose, denied_reason.
        """
        with self._lock.acquire():
            data = self._read_registry()
        return data.get("blocklist", [])

    def add_to_blocklist(
        self,
        name: str,
        version: str = "*",
        source_url: str = "",
        purpose: str = "",
        denied_reason: str = "",
    ) -> None:
        """Add a skill to the blocklist and auto-deny if registered."""
        entry = {
            "name": name,
            "version": version,
            "source_url": source_url,
            "purpose": purpose,
            "denied_reason": denied_reason,
            "added_at": _now_iso(),
        }

        with self._lock.acquire():
            data = self._read_registry()
            # Avoid duplicates
            existing_names = {b["name"] for b in data.get("blocklist", [])}
            if name not in existing_names:
                data.setdefault("blocklist", []).append(entry)
                logger.info("Added '%s' to blocklist", name)

            # Auto-deny if already registered
            if name in data["skills"]:
                data["skills"][name]["status"] = "denied"
                data["skills"][name]["denied_reason"] = (
                    denied_reason or "Added to blocklist."
                )
                data["skills"][name]["audit_notes"] = (
                    f"Auto-denied: added to blocklist on {_now_iso()}"
                )
                logger.warning("Skill '%s' auto-denied (added to blocklist)", name)

            data["metadata"]["last_modified"] = _now_iso()
            self._write_registry(data)

    def remove_from_blocklist(self, name: str) -> bool:
        """Remove a skill from the blocklist. Returns True if found and removed."""
        with self._lock.acquire():
            data = self._read_registry()
            original_len = len(data.get("blocklist", []))
            data["blocklist"] = [
                b for b in data.get("blocklist", []) if b["name"] != name
            ]
            removed = len(data["blocklist"]) < original_len
            if removed:
                data["metadata"]["last_modified"] = _now_iso()
                self._write_registry(data)
                logger.info("Removed '%s' from blocklist", name)
        return removed

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def compute_skill_hash(self, skill_path: str) -> str:
        """Compute SHA-256 hash of all files in a skill directory."""
        skill_dir = Path(skill_path).resolve()
        if not skill_dir.is_dir():
            return ""
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(skill_dir):
            dirs[:] = [
                d for d in sorted(dirs)
                if d not in {"__pycache__", ".git", "node_modules"}
            ]
            for fname in sorted(files):
                fpath = Path(root) / fname
                try:
                    hasher.update(fpath.read_bytes())
                except OSError:
                    continue
        return hasher.hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _seed_blocklist(self) -> None:
        """Ensure the initial blocklist entries are present."""
        with self._lock.acquire():
            data = self._read_registry()
            existing = {b["name"] for b in data.get("blocklist", [])}
            added = 0
            for item in INITIAL_BLOCKLIST:
                if item["name"] not in existing:
                    data.setdefault("blocklist", []).append({
                        **item,
                        "version": item.get("version", "*"),
                        "added_at": _now_iso(),
                    })
                    added += 1
            if added > 0:
                data["metadata"]["last_modified"] = _now_iso()
                self._write_registry(data)
                logger.info("Seeded %d entries into blocklist", added)

    def _is_blocklisted(self, name: str) -> bool:
        """Check if a skill name appears on the blocklist."""
        with self._lock.acquire():
            data = self._read_registry()
        return any(
            b["name"].lower() == name.lower()
            for b in data.get("blocklist", [])
        )

    def _set_status(
        self, name: str, status: str, notes: str
    ) -> Optional[SkillEntry]:
        """Internal: update a skill's status and notes."""
        now = _now_iso()
        with self._lock.acquire():
            data = self._read_registry()
            skill = data["skills"].get(name)
            if skill is None:
                logger.warning("Skill '%s' not found in registry", name)
                return None
            skill["status"] = status
            skill["last_audit_date"] = now
            if notes:
                skill["audit_notes"] = notes
            data["metadata"]["last_modified"] = now
            self._write_registry(data)
        logger.info("Skill '%s' status → %s", name, status)
        return SkillEntry.from_dict(skill)

    def _read_registry(self) -> Dict[str, Any]:
        """Read the JSON registry file. Caller must hold the lock."""
        try:
            raw = self._path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read registry %s: %s", self._path, exc)
            return {"skills": {}, "blocklist": [], "metadata": {}}

    def _write_registry(self, data: Dict[str, Any]) -> None:
        """Write the JSON registry file atomically. Caller must hold the lock."""
        tmp_path = self._path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False),
                encoding="utf-8",
            )
            # Atomic rename (works on same filesystem)
            tmp_path.replace(self._path)
        except OSError as exc:
            logger.error("Failed to write registry %s: %s", self._path, exc)
            # Clean up temp file
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
