"""
Skill Scanner - Static analysis module for scanning community skills/plugins for malware.

Detects obfuscated shell commands, suspicious network calls, Base64-encoded payloads,
known malicious patterns (including Atomic Stealer signatures from the ClawHub audit),
and blocklisted dependencies.

All imports are from the Python standard library.

Created: February 9, 2026
"""

import ast
import base64
import hashlib
import logging
import os
import re
import stat
import tokenize
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scan result
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A single security finding from a scan."""
    severity: str          # "critical", "high", "medium", "low", "info"
    category: str          # e.g. "obfuscated_shell", "base64_payload", ...
    file: str              # relative path inside the skill directory
    line: int              # 1-based line number (0 if not applicable)
    description: str       # human-readable explanation
    evidence: str = ""     # the offending snippet (truncated)

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.file}:{self.line} - {self.description}"


@dataclass
class ScanResult:
    """Aggregated result of scanning a skill or plugin directory."""
    skill_path: str
    passed: bool
    risk_level: str          # "safe", "low", "medium", "high", "critical"
    findings: List[Finding] = field(default_factory=list)
    scanned_files: int = 0
    sha256_hash: str = ""    # hash of concatenated file contents (for integrity)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")


# ---------------------------------------------------------------------------
# Known malicious patterns — sourced from ClawHub audit, Atomic Stealer IOCs,
# and common supply-chain attack vectors found in community plugins.
# ---------------------------------------------------------------------------

KNOWN_MALICIOUS_PATTERNS: List[Dict[str, str]] = [
    # -- Atomic Stealer / AMOS signatures (macOS credential stealer) -----------
    {
        "name": "atomic_stealer_osascript_prompt",
        "pattern": r"""osascript\s+-e\s+['"].*display\s+dialog.*password""",
        "severity": "critical",
        "description": "Atomic Stealer (AMOS) pattern: osascript dialog harvesting passwords",
    },
    {
        "name": "atomic_stealer_keychain_dump",
        "pattern": r"""security\s+find-(generic|internet)-password\s+-[gwa]""",
        "severity": "critical",
        "description": "Atomic Stealer: macOS Keychain credential extraction",
    },
    {
        "name": "atomic_stealer_browser_theft",
        "pattern": r"""(Cookies|Login\s*Data|Local\s*State).*Chromium|Google.*Chrome""",
        "severity": "high",
        "description": "Atomic Stealer: browser credential / cookie file access",
    },
    {
        "name": "atomic_stealer_crypto_wallet",
        "pattern": r"""(Electrum|Exodus|Coinomi|Atomic\s*Wallet|Metamask).*wallet""",
        "severity": "high",
        "description": "Atomic Stealer: cryptocurrency wallet file access pattern",
    },

    # -- ClawHub audit: obfuscated installer payloads ----------------------------
    {
        "name": "clawhub_fake_prereq_install",
        "pattern": (
            r"""(?:curl|wget)\s+(?:-[sSfLkO]+\s+)*https?://"""
            r"""(?!(?:pypi\.org|github\.com|githubusercontent\.com|"""
            r"""registry\.npmjs\.org|raw\.githubusercontent\.com)/)"""
            r"""[^\s'"]+\s*\|\s*(?:ba)?sh"""
        ),
        "severity": "critical",
        "description": (
            "ClawHub audit: download piped to shell from non-approved domain "
            "(fake prerequisite installer pattern)"
        ),
    },
    {
        "name": "clawhub_encoded_downloader",
        "pattern": (
            r"""(?:echo|printf)\s+['\"]?[A-Za-z0-9+/=]{40,}['\"]?\s*\|\s*"""
            r"""base64\s+(?:-d|--decode)\s*\|\s*(?:ba)?sh"""
        ),
        "severity": "critical",
        "description": (
            "ClawHub audit: Base64-encoded payload decoded and executed via shell"
        ),
    },
    {
        "name": "clawhub_credential_exfil",
        "pattern": (
            r"""(?:curl|wget|fetch|httpx?)\s+.*(?:--data|--post-data|-d)\s+.*"""
            r"""(?:password|passwd|token|secret|key|credential|cookie)"""
        ),
        "severity": "critical",
        "description": "ClawHub audit: credential exfiltration via HTTP POST",
    },
    {
        "name": "clawhub_env_exfil",
        "pattern": (
            r"""(?:os\.environ|process\.env|ENV\[).*(?:curl|requests\.|fetch|httpx)"""
        ),
        "severity": "high",
        "description": "ClawHub audit: environment variable harvesting followed by network send",
    },
    {
        "name": "clawhub_hidden_reverse_shell",
        "pattern": (
            r"""(?:socket\.socket|subprocess\.Popen|os\.dup2).*"""
            r"""(?:connect|shell|/bin/(?:ba)?sh)"""
        ),
        "severity": "critical",
        "description": "ClawHub audit: reverse shell payload (socket + shell)",
    },

    # -- Generic supply-chain attack vectors ------------------------------------
    {
        "name": "python_exec_obfuscation",
        "pattern": r"""exec\s*\(\s*(?:compile|__import__|base64\.|codecs\.)""",
        "severity": "high",
        "description": "Obfuscated exec() call with compile/import/base64 indirection",
    },
    {
        "name": "python_code_object_injection",
        "pattern": r"""types\.CodeType\s*\(|marshal\.loads\s*\(""",
        "severity": "critical",
        "description": "Direct code object construction / marshal deserialization",
    },
    {
        "name": "eval_base64_decode",
        "pattern": r"""eval\s*\(\s*(?:base64\.b64decode|codecs\.decode)""",
        "severity": "critical",
        "description": "eval() of Base64 or codecs decoded content",
    },
    {
        "name": "subprocess_hidden_shell",
        "pattern": (
            r"""subprocess\.(?:Popen|call|run|check_output)\s*\("""
            r""".*shell\s*=\s*True"""
        ),
        "severity": "medium",
        "description": "subprocess with shell=True (potential command injection)",
    },
    {
        "name": "dns_exfil_pattern",
        "pattern": r"""\.encode\(.*\)\.hex\(\).*\..*\.(?:com|net|org|xyz|io)""",
        "severity": "high",
        "description": "DNS exfiltration pattern: hex-encoding data into domain names",
    },
    {
        "name": "telegram_exfil",
        "pattern": r"""api\.telegram\.org/bot.*sendDocument|sendMessage""",
        "severity": "critical",
        "description": "Data exfiltration via Telegram bot API",
    },
    {
        "name": "discord_webhook_exfil",
        "pattern": r"""discord(?:app)?\.com/api/webhooks/\d+/""",
        "severity": "critical",
        "description": "Data exfiltration via Discord webhook",
    },
    {
        "name": "pip_install_url",
        "pattern": r"""pip\s+install\s+(?:--index-url|--extra-index-url)\s+https?://(?!pypi\.org)""",
        "severity": "high",
        "description": "pip install from non-PyPI index (dependency confusion attack)",
    },
    {
        "name": "setup_py_backdoor",
        "pattern": r"""class\s+\w*install\w*\(.*install\).*\n.*def\s+run\s*\(""",
        "severity": "high",
        "description": "Custom setup.py install command override (potential backdoor)",
    },
    {
        "name": "powershell_encoded_command",
        "pattern": r"""powershell.*-(?:e|enc|encodedcommand)\s+[A-Za-z0-9+/=]{20,}""",
        "severity": "critical",
        "description": "PowerShell encoded command execution",
    },
    {
        "name": "ssh_key_theft",
        "pattern": r"""['"](/(?:root|home/\w+)/\.ssh/(?:id_rsa|id_ed25519|authorized_keys))['"]""",
        "severity": "critical",
        "description": "SSH key file access pattern",
    },
]

# Pre-compiled regex cache (compiled lazily on first use)
_COMPILED_PATTERNS: Optional[List[Tuple[Dict[str, str], re.Pattern]]] = None


def _get_compiled_patterns() -> List[Tuple[Dict[str, str], re.Pattern]]:
    """Return compiled regex patterns (cached after first call)."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS is None:
        _COMPILED_PATTERNS = []
        for entry in KNOWN_MALICIOUS_PATTERNS:
            try:
                compiled = re.compile(entry["pattern"], re.IGNORECASE | re.DOTALL)
                _COMPILED_PATTERNS.append((entry, compiled))
            except re.error as exc:
                logger.warning("Failed to compile pattern %s: %s", entry["name"], exc)
    return _COMPILED_PATTERNS


# ---------------------------------------------------------------------------
# Approved domains for network calls
# ---------------------------------------------------------------------------

APPROVED_DOMAINS: Set[str] = {
    "pypi.org",
    "github.com",
    "raw.githubusercontent.com",
    "githubusercontent.com",
    "registry.npmjs.org",
    "api.mycosoft.com",
    "mycosoft.com",
    "192.168.0.187",
    "192.168.0.188",
    "192.168.0.189",
    "localhost",
    "127.0.0.1",
}

# ---------------------------------------------------------------------------
# Blocklisted dependencies (known typosquats and malicious packages)
# ---------------------------------------------------------------------------

BLOCKLISTED_PACKAGES: Set[str] = {
    # Python typosquats / known malicious from PyPI takedowns
    "python-binance-sdk",       # credential stealer
    "colorama-dev",             # typosquat
    "requests-toolbet",         # typosquat of requests-toolbelt
    "python3-dateutil",         # typosquat of python-dateutil
    "jeIlyfish",                # typosquat of jellyfish (capital I vs l)
    "python-sqlite",            # credential stealer
    "coloursama",               # typosquat of colorama
    "pipsqlite",                # data exfil
    "libpeshka",                # crypto miner
    "libari",                   # W4SP stealer
    "libesa",                   # W4SP stealer
    "libphp",                   # W4SP stealer
    "colorwin",                 # W4SP stealer
    "cypherium",                # credential stealer
    "web3-essential",           # credential stealer
    "importantpackage",         # reverse shell PoC
    "ctx",                      # environment variable stealer (2022 hijack)
    "atomicstealer",            # AMOS payload wrapper
    # npm typosquats
    "crossenv",                 # env stealer
    "event-stream-malicious",   # backdoor (event-stream incident)
    "ua-parser-js-malicious",   # hijacked version
}

# ---------------------------------------------------------------------------
# File extensions to scan
# ---------------------------------------------------------------------------

SCANNABLE_EXTENSIONS: Set[str] = {
    ".py", ".pyw", ".js", ".ts", ".mjs", ".cjs",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".md", ".txt", ".rst",
    ".dockerfile", ".Dockerfile",
}

BINARY_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".pyc", ".pyo", ".whl", ".egg",
}

# ---------------------------------------------------------------------------
# SkillScanner
# ---------------------------------------------------------------------------


class SkillScanner:
    """
    Static analysis scanner for community skills and plugins.

    Scans skill directories for:
    - Obfuscated shell commands (curl/wget piped to sh/bash)
    - Suspicious network calls to non-approved domains
    - Base64-encoded payloads that decode to malicious content
    - Known malicious patterns (Atomic Stealer, ClawHub audit IOCs)
    - Blocklisted dependencies
    - Suspicious Python AST constructs
    - Binary/compiled files that shouldn't be in a skill
    """

    def __init__(
        self,
        approved_domains: Optional[Set[str]] = None,
        blocklisted_packages: Optional[Set[str]] = None,
        extra_patterns: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.approved_domains = approved_domains or APPROVED_DOMAINS
        self.blocklisted_packages = blocklisted_packages or BLOCKLISTED_PACKAGES
        self._extra_patterns = extra_patterns or []
        logger.info("SkillScanner initialized (approved_domains=%d, blocklist=%d)",
                     len(self.approved_domains), len(self.blocklisted_packages))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_skill(self, skill_path: str) -> ScanResult:
        """
        Scan a single skill directory and return a ScanResult.

        Parameters
        ----------
        skill_path : str
            Absolute or relative path to the skill directory.

        Returns
        -------
        ScanResult
            Aggregated scan result with findings, risk level, and pass/fail.
        """
        skill_dir = Path(skill_path).resolve()
        if not skill_dir.exists():
            logger.error("Skill path does not exist: %s", skill_dir)
            return ScanResult(
                skill_path=str(skill_dir),
                passed=False,
                risk_level="critical",
                findings=[Finding(
                    severity="critical",
                    category="path_error",
                    file=str(skill_dir),
                    line=0,
                    description=f"Skill path does not exist: {skill_dir}",
                )],
            )

        findings: List[Finding] = []
        scanned = 0
        hasher = hashlib.sha256()

        for file_path in self._iter_files(skill_dir):
            rel = str(file_path.relative_to(skill_dir))
            ext = file_path.suffix.lower()

            # Flag unexpected binaries
            if ext in BINARY_EXTENSIONS:
                findings.append(Finding(
                    severity="high",
                    category="binary_file",
                    file=rel,
                    line=0,
                    description=f"Binary/compiled file in skill: {file_path.name}",
                ))
                scanned += 1
                continue

            if ext not in SCANNABLE_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("Cannot read %s: %s", file_path, exc)
                continue

            scanned += 1
            hasher.update(content.encode("utf-8", errors="replace"))

            # Run all detectors
            findings.extend(self._detect_malicious_patterns(content, rel))
            findings.extend(self._detect_obfuscated_shell(content, rel))
            findings.extend(self._detect_suspicious_network(content, rel))
            findings.extend(self._detect_base64_payloads(content, rel))
            findings.extend(self._detect_blocklisted_deps(content, rel, ext))

            if ext == ".py":
                findings.extend(self._analyze_python_ast(content, rel))

            # Check file permissions on Unix
            if os.name != "nt":
                findings.extend(self._check_file_permissions(file_path, rel))

        risk = self._compute_risk(findings)
        passed = risk in ("safe", "low")

        result = ScanResult(
            skill_path=str(skill_dir),
            passed=passed,
            risk_level=risk,
            findings=findings,
            scanned_files=scanned,
            sha256_hash=hasher.hexdigest(),
        )

        logger.info(
            "Scan complete: %s — %d files, %d findings, risk=%s, passed=%s",
            skill_dir.name, scanned, len(findings), risk, passed,
        )
        return result

    def scan_directory(self, dir_path: str) -> List[ScanResult]:
        """
        Batch-scan all immediate subdirectories as individual skills.

        Parameters
        ----------
        dir_path : str
            Directory containing multiple skill subdirectories.

        Returns
        -------
        List[ScanResult]
            One ScanResult per subdirectory.
        """
        base = Path(dir_path).resolve()
        if not base.is_dir():
            logger.error("Directory does not exist: %s", base)
            return []

        results: List[ScanResult] = []
        for child in sorted(base.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                logger.info("Scanning skill: %s", child.name)
                results.append(self.scan_skill(str(child)))

        logger.info("Batch scan complete: %d skills scanned", len(results))
        return results

    # ------------------------------------------------------------------
    # Detection methods
    # ------------------------------------------------------------------

    def _detect_malicious_patterns(
        self, content: str, rel_path: str
    ) -> List[Finding]:
        """Match content against all known malicious patterns."""
        findings: List[Finding] = []
        for entry, compiled in _get_compiled_patterns():
            for match in compiled.finditer(content):
                line_no = content[:match.start()].count("\n") + 1
                snippet = match.group(0)[:200]
                findings.append(Finding(
                    severity=entry["severity"],
                    category=entry["name"],
                    file=rel_path,
                    line=line_no,
                    description=entry["description"],
                    evidence=snippet,
                ))
        # Also check extra patterns supplied at init
        for entry in self._extra_patterns:
            try:
                pat = re.compile(entry["pattern"], re.IGNORECASE | re.DOTALL)
            except re.error:
                continue
            for match in pat.finditer(content):
                line_no = content[:match.start()].count("\n") + 1
                findings.append(Finding(
                    severity=entry.get("severity", "medium"),
                    category=entry.get("name", "custom_pattern"),
                    file=rel_path,
                    line=line_no,
                    description=entry.get("description", "Custom pattern match"),
                    evidence=match.group(0)[:200],
                ))
        return findings

    def _detect_obfuscated_shell(
        self, content: str, rel_path: str
    ) -> List[Finding]:
        """Detect shell commands piped to interpreters from untrusted sources."""
        findings: List[Finding] = []
        # curl/wget piped to shell
        pipe_to_shell = re.compile(
            r"""(?:curl|wget|fetch)\s+[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh""",
            re.IGNORECASE,
        )
        for match in pipe_to_shell.finditer(content):
            # Check if domain is approved
            url_match = re.search(r"https?://([^/\s'\"]+)", match.group(0))
            domain = url_match.group(1) if url_match else ""
            if not self._is_approved_domain(domain):
                line_no = content[:match.start()].count("\n") + 1
                findings.append(Finding(
                    severity="critical",
                    category="obfuscated_shell",
                    file=rel_path,
                    line=line_no,
                    description=(
                        f"Download piped to shell from unapproved domain: {domain}"
                    ),
                    evidence=match.group(0)[:200],
                ))

        # Encoded shell execution via environment variables
        env_shell = re.compile(
            r"""\$\(.*(?:curl|wget).*\)|`.*(?:curl|wget).*`""",
            re.IGNORECASE,
        )
        for match in env_shell.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            findings.append(Finding(
                severity="high",
                category="obfuscated_shell",
                file=rel_path,
                line=line_no,
                description="Shell command substitution with network download",
                evidence=match.group(0)[:200],
            ))
        return findings

    def _detect_suspicious_network(
        self, content: str, rel_path: str
    ) -> List[Finding]:
        """Flag network calls to non-approved domains."""
        findings: List[Finding] = []
        # Python requests / urllib / httpx / aiohttp
        net_patterns = [
            re.compile(
                r"""(?:requests|urllib\.request|httpx|aiohttp)"""
                r"""\.(?:get|post|put|delete|patch|head|request)\s*\(\s*"""
                r"""['"f](https?://[^'"\s\)]+)""",
                re.IGNORECASE,
            ),
            # JavaScript/TypeScript fetch
            re.compile(
                r"""fetch\s*\(\s*['"` ](https?://[^'"`\s\)]+)""",
                re.IGNORECASE,
            ),
            # Generic URL in curl/wget commands
            re.compile(
                r"""(?:curl|wget)\s+[^\n]*?(https?://[^\s'"]+)""",
                re.IGNORECASE,
            ),
        ]
        for pat in net_patterns:
            for match in pat.finditer(content):
                url = match.group(1)
                domain_match = re.search(r"https?://([^/:]+)", url)
                domain = domain_match.group(1) if domain_match else ""
                if domain and not self._is_approved_domain(domain):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(Finding(
                        severity="high",
                        category="suspicious_network",
                        file=rel_path,
                        line=line_no,
                        description=(
                            f"Network call to unapproved domain: {domain}"
                        ),
                        evidence=match.group(0)[:200],
                    ))
        return findings

    def _detect_base64_payloads(
        self, content: str, rel_path: str
    ) -> List[Finding]:
        """Find Base64 strings, decode them, and check for malicious content."""
        findings: List[Finding] = []
        # Match Base64 strings of significant length (>40 chars)
        b64_pattern = re.compile(
            r"""(?:['"])([A-Za-z0-9+/]{40,}={0,2})(?:['"])"""
        )
        for match in b64_pattern.finditer(content):
            encoded = match.group(1)
            try:
                decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
            except Exception:
                continue

            # Check decoded content for dangerous patterns
            danger_indicators = [
                (r"(?:curl|wget).*\|\s*(?:ba)?sh", "shell download in base64"),
                (r"/bin/(?:ba)?sh", "shell reference in base64"),
                (r"import\s+(?:os|subprocess|socket)", "dangerous import in base64"),
                (r"exec\s*\(", "exec() call in base64"),
                (r"eval\s*\(", "eval() call in base64"),
                (r"(?:password|secret|token|api.key)", "credential keyword in base64"),
                (r"(?:rm\s+-rf|chmod\s+777|dd\s+if=)", "destructive command in base64"),
                (r"(?:nc|ncat|netcat)\s+-[lep]", "netcat listener in base64"),
                (r"socket\.connect", "socket connection in base64"),
                (r"powershell", "PowerShell invocation in base64"),
            ]
            for pattern, desc in danger_indicators:
                if re.search(pattern, decoded, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(Finding(
                        severity="critical",
                        category="base64_payload",
                        file=rel_path,
                        line=line_no,
                        description=f"Base64-decoded content contains: {desc}",
                        evidence=decoded[:200],
                    ))
                    break  # one finding per b64 string is enough
        return findings

    def _detect_blocklisted_deps(
        self, content: str, rel_path: str, ext: str
    ) -> List[Finding]:
        """Check dependency files for blocklisted packages."""
        findings: List[Finding] = []
        dep_files = {
            "requirements.txt", "setup.py", "setup.cfg", "pyproject.toml",
            "Pipfile", "package.json", "package-lock.json",
        }
        filename = Path(rel_path).name.lower()
        if filename not in dep_files and ext not in (".py", ".js", ".ts"):
            return findings

        lower_content = content.lower()
        for pkg in self.blocklisted_packages:
            if pkg.lower() in lower_content:
                # Find the line
                for i, line in enumerate(content.splitlines(), 1):
                    if pkg.lower() in line.lower():
                        findings.append(Finding(
                            severity="critical",
                            category="blocklisted_dependency",
                            file=rel_path,
                            line=i,
                            description=(
                                f"Blocklisted package found: {pkg}"
                            ),
                            evidence=line.strip()[:200],
                        ))
                        break
        return findings

    def _analyze_python_ast(
        self, content: str, rel_path: str
    ) -> List[Finding]:
        """Use Python AST analysis to detect dangerous constructs."""
        findings: List[Finding] = []
        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError:
            # Not valid Python; skip AST analysis
            return findings

        for node in ast.walk(tree):
            # Detect eval() / exec() calls
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in ("eval", "exec", "compile"):
                    findings.append(Finding(
                        severity="medium",
                        category="dangerous_builtin",
                        file=rel_path,
                        line=getattr(node, "lineno", 0),
                        description=f"Call to {func_name}() detected",
                    ))
                # Detect __import__ calls (dynamic imports)
                elif func_name == "__import__":
                    findings.append(Finding(
                        severity="high",
                        category="dynamic_import",
                        file=rel_path,
                        line=getattr(node, "lineno", 0),
                        description="Dynamic __import__() call detected",
                    ))
                # Detect os.system, os.popen, subprocess.Popen
                elif func_name in (
                    "os.system", "os.popen", "os.execv", "os.execve",
                    "os.execvp", "os.execvpe", "os.spawnl", "os.spawnle",
                    "subprocess.Popen", "subprocess.call",
                    "subprocess.check_output", "subprocess.run",
                ):
                    findings.append(Finding(
                        severity="medium",
                        category="shell_execution",
                        file=rel_path,
                        line=getattr(node, "lineno", 0),
                        description=f"System command execution via {func_name}()",
                    ))

            # Detect dangerous imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("ctypes", "cffi", "mmap"):
                        findings.append(Finding(
                            severity="medium",
                            category="dangerous_import",
                            file=rel_path,
                            line=getattr(node, "lineno", 0),
                            description=f"Import of low-level module: {alias.name}",
                        ))

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(("ctypes", "cffi")):
                    findings.append(Finding(
                        severity="medium",
                        category="dangerous_import",
                        file=rel_path,
                        line=getattr(node, "lineno", 0),
                        description=f"Import from low-level module: {node.module}",
                    ))

        return findings

    def _check_file_permissions(
        self, file_path: Path, rel_path: str
    ) -> List[Finding]:
        """Check for overly permissive file permissions (Unix only)."""
        findings: List[Finding] = []
        try:
            mode = file_path.stat().st_mode
            if mode & stat.S_IWOTH:
                findings.append(Finding(
                    severity="medium",
                    category="file_permissions",
                    file=rel_path,
                    line=0,
                    description="File is world-writable",
                ))
            if mode & stat.S_ISUID:
                findings.append(Finding(
                    severity="high",
                    category="file_permissions",
                    file=rel_path,
                    line=0,
                    description="File has setuid bit set",
                ))
        except OSError:
            pass
        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_approved_domain(self, domain: str) -> bool:
        """Check if a domain (or IP) is in the approved list."""
        if not domain:
            return False
        domain_lower = domain.lower().rstrip(".")
        for approved in self.approved_domains:
            if domain_lower == approved or domain_lower.endswith("." + approved):
                return True
        return False

    @staticmethod
    def _get_call_name(node: ast.Call) -> str:
        """Extract the function name from an AST Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    @staticmethod
    def _iter_files(directory: Path):
        """Yield all files in directory, skipping hidden dirs and __pycache__."""
        skip_dirs = {"__pycache__", ".git", ".svn", "node_modules", ".venv", "venv"}
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for f in files:
                yield Path(root) / f

    @staticmethod
    def _compute_risk(findings: List[Finding]) -> str:
        """Determine overall risk level from findings."""
        if not findings:
            return "safe"
        severities = {f.severity for f in findings}
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"
