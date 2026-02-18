"""
Skill Registry - Allow-list / deny-list registry for approved community skills.

Stores skill metadata and audit status in a JSON file. Provides methods to
register, approve, deny, and audit skills (integrating with SkillScanner).
Thread-safe with file locking.

All imports are from the Python standard library.

Created: February 9, 2026
Updated: February 17, 2026 - Added PERMISSIONS.json loading and validation for MYCA
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
import fnmatch
import jsonschema

from .skill_scanner import ScanResult, SkillScanner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MYCA Permissions Integration
# ---------------------------------------------------------------------------

MYCA_SKILL_PERMISSIONS_DIR = Path(__file__).resolve().parent.parent / "myca" / "skill_permissions"
PERMISSIONS_SCHEMA_PATH = MYCA_SKILL_PERMISSIONS_DIR / "_schema" / "PERMISSIONS.schema.json"

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
# MYCA Skill Permissions
# ---------------------------------------------------------------------------


@dataclass
class SkillPermissions:
    """Permission manifest for a MYCA skill."""
    name: str
    version: str
    description: str
    risk_tier: str                       # "low", "medium", "high", "critical"
    tools_allow: List[str]
    tools_deny: List[str]
    filesystem_read: List[str]
    filesystem_write: List[str]
    filesystem_deny: List[str]
    network_enabled: bool
    network_allowlist: List[str]
    network_denylist: List[str]
    secrets_allowed_scopes: List[str]
    max_runtime_seconds: int
    max_files_written: int
    max_bytes_written: int
    sandbox_required: bool
    dependencies: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillPermissions":
        """Parse PERMISSIONS.json into SkillPermissions."""
        tools = data.get("tools", {})
        fs = data.get("filesystem", {})
        net = data.get("network", {})
        secrets = data.get("secrets", {})
        limits = data.get("limits", {})
        
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            risk_tier=data.get("risk_tier", "low"),
            tools_allow=tools.get("allow", []),
            tools_deny=tools.get("deny", []),
            filesystem_read=fs.get("read_paths", []),
            filesystem_write=fs.get("write_paths", []),
            filesystem_deny=fs.get("deny_paths", []),
            network_enabled=net.get("enabled", False),
            network_allowlist=net.get("allowlist", []),
            network_denylist=net.get("denylist", []),
            secrets_allowed_scopes=secrets.get("allowed_scopes", []),
            max_runtime_seconds=limits.get("max_runtime_seconds", 30),
            max_files_written=limits.get("max_files_written", 10),
            max_bytes_written=limits.get("max_bytes_written", 100000),
            sandbox_required=limits.get("sandbox_required", False),
            dependencies=data.get("dependencies", []),
            reviewers=data.get("reviewers", []),
        )
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this skill."""
        # Deny list takes precedence
        if tool_name in self.tools_deny:
            return False
        # Check allow list (supports wildcard)
        if "*" in self.tools_allow:
            return True
        return tool_name in self.tools_allow
    
    def is_path_allowed(self, path: str, mode: str = "read") -> bool:
        """Check if a filesystem path is allowed. mode: 'read' or 'write'."""
        path = str(Path(path).resolve())
        
        # Deny list takes precedence
        for pattern in self.filesystem_deny:
            if self._path_matches(path, pattern):
                return False
        
        # Check allowed paths
        allowed = self.filesystem_read if mode == "read" else self.filesystem_write
        for pattern in allowed:
            if self._path_matches(path, pattern):
                return True
        return False
    
    def is_network_allowed(self, url: str) -> bool:
        """Check if a network URL is allowed."""
        if not self.network_enabled:
            return False
        
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or url
        
        # Denylist takes precedence
        for pattern in self.network_denylist:
            if fnmatch.fnmatch(domain, pattern):
                return False
        
        # Check allowlist
        for allowed in self.network_allowlist:
            # Exact match or prefix match for full URLs
            if domain == allowed or url.startswith(allowed):
                return True
        return False
    
    def is_secret_scope_allowed(self, scope: str) -> bool:
        """Check if a secret scope is allowed."""
        return scope in self.secrets_allowed_scopes
    
    @staticmethod
    def _path_matches(path: str, pattern: str) -> bool:
        """Check if path matches pattern (supports glob)."""
        pattern = str(Path(pattern).expanduser())
        return fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("*"))


class PermissionValidator:
    """Validates skill permissions against the schema and enforces rules."""
    
    def __init__(self):
        self._schema: Optional[Dict[str, Any]] = None
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load the PERMISSIONS.schema.json file."""
        if PERMISSIONS_SCHEMA_PATH.exists():
            try:
                self._schema = json.loads(PERMISSIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
                logger.info("Loaded MYCA permissions schema from %s", PERMISSIONS_SCHEMA_PATH)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load permissions schema: %s", e)
    
    def validate_schema(self, permissions_data: Dict[str, Any]) -> List[str]:
        """Validate permissions data against JSON schema. Returns list of errors."""
        if not self._schema:
            return ["Permissions schema not loaded"]
        
        errors = []
        try:
            jsonschema.validate(permissions_data, self._schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        return errors
    
    def validate_rules(self, permissions: SkillPermissions) -> List[str]:
        """Validate semantic rules beyond schema. Returns list of errors/warnings."""
        errors = []
        
        # Rule 2: Risk tier consistency
        if permissions.risk_tier in ("high", "critical") and not permissions.sandbox_required:
            errors.append(f"ERROR: {permissions.risk_tier} risk skill must have sandbox_required=true")
        
        # Rule 3: Network allowlist required if enabled
        if permissions.network_enabled and not permissions.network_allowlist:
            errors.append("ERROR: network.enabled=true but allowlist is empty")
        
        # Rule 4: Standard sensitive paths should be denied
        required_deny = ["~/.ssh", "~/.aws", "~/.config", "/etc", "/var", "/proc"]
        missing = [p for p in required_deny if p not in permissions.filesystem_deny]
        if missing:
            errors.append(f"WARN: Missing standard deny paths: {missing}")
        
        # Rule 6: Contradictory tool entries
        contradictions = set(permissions.tools_allow) & set(permissions.tools_deny)
        if contradictions:
            errors.append(f"WARN: Tools in both allow and deny: {contradictions}")
        
        return errors
    
    def load_skill_permissions(self, skill_name: str) -> Optional[SkillPermissions]:
        """Load PERMISSIONS.json for a skill."""
        skill_dir = MYCA_SKILL_PERMISSIONS_DIR / skill_name
        perm_file = skill_dir / "PERMISSIONS.json"
        
        if not perm_file.exists():
            logger.debug("No PERMISSIONS.json for skill '%s'", skill_name)
            return None
        
        try:
            data = json.loads(perm_file.read_text(encoding="utf-8"))
            return SkillPermissions.from_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load permissions for '%s': %s", skill_name, e)
            return None
    
    def get_all_skill_permissions(self) -> Dict[str, SkillPermissions]:
        """Load all skill permissions from the myca/skill_permissions directory."""
        result = {}
        if not MYCA_SKILL_PERMISSIONS_DIR.exists():
            return result
        
        for skill_dir in MYCA_SKILL_PERMISSIONS_DIR.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                perm = self.load_skill_permissions(skill_dir.name)
                if perm:
                    result[skill_dir.name] = perm
        
        return result


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
    
    MYCA Integration (Feb 17, 2026):
    - Loads PERMISSIONS.json from myca/skill_permissions/
    - Validates permissions against schema and semantic rules
    - Provides permission enforcement methods
    """

    def __init__(
        self,
        registry_path: Optional[str] = None,
        scanner: Optional[SkillScanner] = None,
    ) -> None:
        self._path = Path(registry_path) if registry_path else _DEFAULT_REGISTRY_PATH
        self._lock = _FileLock(str(self._path) + ".lock")
        self._scanner = scanner or SkillScanner()
        
        # MYCA permission validator
        self._permission_validator = PermissionValidator()
        self._skill_permissions: Dict[str, SkillPermissions] = {}

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
        
        # Load MYCA skill permissions
        self._load_myca_permissions()

        logger.info("SkillRegistry initialized: %s", self._path)
    
    # ------------------------------------------------------------------
    # MYCA Permission Loading
    # ------------------------------------------------------------------
    
    def _load_myca_permissions(self) -> None:
        """Load all MYCA skill permissions from skill_permissions directory."""
        self._skill_permissions = self._permission_validator.get_all_skill_permissions()
        if self._skill_permissions:
            logger.info("Loaded MYCA permissions for %d skills", len(self._skill_permissions))
    
    def get_skill_permissions(self, skill_name: str) -> Optional[SkillPermissions]:
        """Get the permissions for a skill."""
        return self._skill_permissions.get(skill_name)
    
    def reload_permissions(self) -> int:
        """Reload all MYCA permissions. Returns count of loaded permissions."""
        self._load_myca_permissions()
        return len(self._skill_permissions)
    
    def check_tool_permission(
        self,
        skill_name: str,
        tool_name: str,
    ) -> tuple[bool, str]:
        """
        Check if a skill is allowed to use a tool.
        
        Returns (allowed, reason).
        """
        perm = self._skill_permissions.get(skill_name)
        if not perm:
            # No permissions defined - default deny for MYCA skills
            return False, f"No PERMISSIONS.json for skill '{skill_name}'"
        
        if perm.is_tool_allowed(tool_name):
            return True, "Allowed by PERMISSIONS.json"
        else:
            return False, f"Tool '{tool_name}' denied for skill '{skill_name}'"
    
    def check_path_permission(
        self,
        skill_name: str,
        path: str,
        mode: str = "read",
    ) -> tuple[bool, str]:
        """
        Check if a skill is allowed to access a filesystem path.
        
        Args:
            skill_name: Name of the skill
            path: Filesystem path
            mode: "read" or "write"
            
        Returns (allowed, reason).
        """
        perm = self._skill_permissions.get(skill_name)
        if not perm:
            return False, f"No PERMISSIONS.json for skill '{skill_name}'"
        
        if perm.is_path_allowed(path, mode):
            return True, f"Path {mode} allowed by PERMISSIONS.json"
        else:
            return False, f"Path '{path}' ({mode}) denied for skill '{skill_name}'"
    
    def check_network_permission(
        self,
        skill_name: str,
        url: str,
    ) -> tuple[bool, str]:
        """
        Check if a skill is allowed to access a network URL.
        
        Returns (allowed, reason).
        """
        perm = self._skill_permissions.get(skill_name)
        if not perm:
            return False, f"No PERMISSIONS.json for skill '{skill_name}'"
        
        if perm.is_network_allowed(url):
            return True, "URL allowed by PERMISSIONS.json"
        else:
            return False, f"URL '{url}' denied for skill '{skill_name}'"
    
    def check_secret_permission(
        self,
        skill_name: str,
        scope: str,
    ) -> tuple[bool, str]:
        """
        Check if a skill is allowed to access a secret scope.
        
        Returns (allowed, reason).
        """
        perm = self._skill_permissions.get(skill_name)
        if not perm:
            return False, f"No PERMISSIONS.json for skill '{skill_name}'"
        
        if perm.is_secret_scope_allowed(scope):
            return True, f"Secret scope '{scope}' allowed"
        else:
            return False, f"Secret scope '{scope}' denied for skill '{skill_name}'"
    
    def requires_sandbox(self, skill_name: str) -> bool:
        """Check if a skill requires sandbox execution."""
        perm = self._skill_permissions.get(skill_name)
        return perm.sandbox_required if perm else False
    
    def get_risk_tier(self, skill_name: str) -> str:
        """Get the risk tier for a skill."""
        perm = self._skill_permissions.get(skill_name)
        return perm.risk_tier if perm else "unknown"

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
