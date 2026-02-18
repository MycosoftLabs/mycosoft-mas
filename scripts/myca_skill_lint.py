#!/usr/bin/env python3
"""
MYCA Skill Permission Linter

Validates PERMISSIONS.json files against the schema and semantic rules.
Run this before committing changes to skill permissions.

Usage:
    python scripts/myca_skill_lint.py
    python scripts/myca_skill_lint.py --strict
    python scripts/myca_skill_lint.py --skill file_editor

Date: February 17, 2026
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Optional

# Try to import jsonschema
try:
    from jsonschema import Draft7Validator, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft7Validator = None
    ValidationError = Exception


# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
MYCA_DIR = PROJECT_ROOT / "mycosoft_mas" / "myca"
SKILL_PERMISSIONS_DIR = MYCA_DIR / "skill_permissions"
SCHEMA_PATH = SKILL_PERMISSIONS_DIR / "_schema" / "PERMISSIONS.schema.json"


# ---------------------------------------------------------------------------
# Lint Rules
# ---------------------------------------------------------------------------

@dataclass
class LintIssue:
    """A single lint issue."""
    skill: str
    rule: str
    severity: str  # error, warning, info
    message: str
    path: Optional[str] = None


@dataclass
class LintResult:
    """Result of linting a skill permission file."""
    skill: str
    file_path: Path
    valid: bool
    issues: list[LintIssue] = field(default_factory=list)


class PermissionLinter:
    """Lints PERMISSIONS.json files against schema and semantic rules."""
    
    # Dangerous tools that require special attention
    DANGEROUS_TOOLS = [
        "merge_pr",
        "force_push",
        "delete_branch",
        "delete_file_permanent",
        "execute_command",
        "execute_shell",
        "run_arbitrary_code",
        "modify_system_config",
    ]
    
    # Sensitive path patterns that should typically be denied
    SENSITIVE_PATHS = [
        "**/.env*",
        "**/*secret*",
        "**/*credential*",
        "**/*password*",
        "**/.git/**",
        "**/.*_history",
        "**/id_rsa*",
        "**/*.pem",
        "**/*.key",
        "**/config/secrets*",
        "**/credentials.local",
        "/etc/shadow",
        "/etc/passwd",
        "~/.aws/**",
        "~/.ssh/**",
    ]
    
    # Secret patterns that should never appear in files
    SECRET_PATTERNS = [
        r"sk-[a-zA-Z0-9]{48}",
        r"sk-ant-[a-zA-Z0-9-]{93}",
        r"AIza[0-9A-Za-z-_]{35}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"AKIA[0-9A-Z]{16}",
    ]
    
    def __init__(self, strict: bool = False):
        """
        Initialize linter.
        
        Args:
            strict: If True, treat warnings as errors.
        """
        self.strict = strict
        self.schema = self._load_schema()
        self.validator = None
        
        if self.schema and JSONSCHEMA_AVAILABLE:
            self.validator = Draft7Validator(self.schema)
    
    def _load_schema(self) -> Optional[dict]:
        """Load the JSON schema."""
        if not SCHEMA_PATH.exists():
            return None
        try:
            return json.loads(SCHEMA_PATH.read_text())
        except json.JSONDecodeError:
            return None
    
    def lint_file(self, perm_file: Path) -> LintResult:
        """
        Lint a single PERMISSIONS.json file.
        
        Args:
            perm_file: Path to the PERMISSIONS.json file.
            
        Returns:
            LintResult with all issues found.
        """
        skill_name = perm_file.parent.name
        result = LintResult(skill=skill_name, file_path=perm_file, valid=True)
        
        # Check file exists
        if not perm_file.exists():
            result.valid = False
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="file_exists",
                severity="error",
                message="PERMISSIONS.json file not found",
            ))
            return result
        
        # Parse JSON
        try:
            data = json.loads(perm_file.read_text())
        except json.JSONDecodeError as e:
            result.valid = False
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="valid_json",
                severity="error",
                message=f"Invalid JSON: {e}",
            ))
            return result
        
        # Schema validation
        if self.validator:
            for error in self.validator.iter_errors(data):
                result.valid = False
                result.issues.append(LintIssue(
                    skill=skill_name,
                    rule="schema_compliance",
                    severity="error",
                    message=error.message,
                    path=".".join(str(p) for p in error.absolute_path),
                ))
        
        # Semantic rules
        self._check_semantic_rules(data, result)
        
        # Update validity based on strict mode
        if self.strict:
            if any(i.severity == "warning" for i in result.issues):
                result.valid = False
        
        return result
    
    def _check_semantic_rules(self, data: dict, result: LintResult) -> None:
        """Check semantic rules beyond JSON schema."""
        skill_name = result.skill
        
        # Rule 1: Risk tier consistency
        risk_tier = data.get("risk_tier", "medium")
        limits = data.get("limits", {})
        secrets = data.get("secrets", {})
        network = data.get("network", {})
        tools = data.get("tools", {})
        
        # High risk must require sandbox
        if risk_tier == "high" and not limits.get("sandbox_required", False):
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="risk_tier_sandbox",
                severity="error",
                message="High risk tier requires sandbox_required=true",
                path="limits.sandbox_required",
            ))
            result.valid = False
        
        # Low risk should not have secret access
        if risk_tier == "low" and secrets.get("allowed_scopes"):
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="low_risk_secrets",
                severity="warning",
                message="Low risk tier should not have secret access",
                path="secrets.allowed_scopes",
            ))
        
        # Rule 2: Network allowlist required when enabled
        if network.get("enabled", False):
            if not network.get("allowlist"):
                result.issues.append(LintIssue(
                    skill=skill_name,
                    rule="network_allowlist",
                    severity="error",
                    message="Network enabled but no allowlist defined",
                    path="network.allowlist",
                ))
                result.valid = False
        
        # Rule 3: Sensitive paths should be denied
        filesystem = data.get("filesystem", {})
        deny_paths = filesystem.get("deny", [])
        
        missing_denies = []
        for sensitive in self.SENSITIVE_PATHS[:5]:  # Check top 5
            found = False
            for deny in deny_paths:
                # Fuzzy match
                if sensitive in deny or deny in sensitive:
                    found = True
                    break
            if not found:
                missing_denies.append(sensitive)
        
        if missing_denies and risk_tier != "low":
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="sensitive_path_deny",
                severity="warning",
                message=f"Consider denying sensitive paths: {missing_denies[:3]}",
                path="filesystem.deny",
            ))
        
        # Rule 4: Dangerous tools should be handled carefully
        allow_list = tools.get("allow", [])
        deny_list = tools.get("deny", [])
        
        for dangerous in self.DANGEROUS_TOOLS:
            if dangerous in allow_list and dangerous not in deny_list:
                if risk_tier != "high":
                    result.issues.append(LintIssue(
                        skill=skill_name,
                        rule="dangerous_tool_risk",
                        severity="error",
                        message=f"Dangerous tool '{dangerous}' requires high risk tier",
                        path="tools.allow",
                    ))
                    result.valid = False
        
        # Rule 5: Deny takes precedence check
        for tool in deny_list:
            if tool in allow_list:
                result.issues.append(LintIssue(
                    skill=skill_name,
                    rule="deny_precedence",
                    severity="info",
                    message=f"Tool '{tool}' in both allow and deny (deny takes precedence)",
                    path="tools",
                ))
        
        # Rule 6: Version format
        version = data.get("version", "")
        if version and not re.match(r"^\d+\.\d+(\.\d+)?$", version):
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="version_format",
                severity="warning",
                message=f"Version '{version}' should be semver (e.g., 1.0.0)",
                path="version",
            ))
        
        # Rule 7: Name format (should match directory)
        name = data.get("name", "")
        if name and name != skill_name:
            result.issues.append(LintIssue(
                skill=skill_name,
                rule="name_match_dir",
                severity="warning",
                message=f"Permission name '{name}' doesn't match directory '{skill_name}'",
                path="name",
            ))
        
        # Rule 8: Check for secret patterns in file (shouldn't have any)
        raw_content = result.file_path.read_text() if result.file_path.exists() else ""
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, raw_content):
                result.issues.append(LintIssue(
                    skill=skill_name,
                    rule="no_secrets",
                    severity="error",
                    message="Permission file appears to contain a secret pattern",
                ))
                result.valid = False
    
    def lint_all(self) -> list[LintResult]:
        """Lint all PERMISSIONS.json files in the skill_permissions directory."""
        results = []
        
        if not SKILL_PERMISSIONS_DIR.exists():
            return results
        
        for skill_dir in SKILL_PERMISSIONS_DIR.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                perm_file = skill_dir / "PERMISSIONS.json"
                if perm_file.exists():
                    results.append(self.lint_file(perm_file))
        
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_result(result: LintResult, verbose: bool = False) -> None:
    """Print a lint result."""
    status = "✓" if result.valid else "✗"
    print(f"{status} {result.skill}")
    
    if result.issues or verbose:
        for issue in result.issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "•")
            path_str = f" ({issue.path})" if issue.path else ""
            print(f"    {icon} [{issue.rule}]{path_str}: {issue.message}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MYCA Skill Permission Linter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--skill",
        "-s",
        help="Lint only this skill",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all details",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    
    args = parser.parse_args()
    
    if not JSONSCHEMA_AVAILABLE:
        print("WARNING: jsonschema not installed. Schema validation will be skipped.")
        print("Install with: pip install jsonschema")
        print()
    
    linter = PermissionLinter(strict=args.strict)
    
    # Lint specific skill or all
    if args.skill:
        perm_file = SKILL_PERMISSIONS_DIR / args.skill / "PERMISSIONS.json"
        results = [linter.lint_file(perm_file)]
    else:
        results = linter.lint_all()
    
    if not results:
        print("No permission files found to lint")
        sys.exit(0)
    
    # Output
    if args.json:
        output = {
            "results": [
                {
                    "skill": r.skill,
                    "valid": r.valid,
                    "issues": [
                        {
                            "rule": i.rule,
                            "severity": i.severity,
                            "message": i.message,
                            "path": i.path,
                        }
                        for i in r.issues
                    ],
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "valid": sum(1 for r in results if r.valid),
                "invalid": sum(1 for r in results if not r.valid),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("MYCA Skill Permission Lint Results")
        print("=" * 40)
        print()
        
        for result in results:
            print_result(result, verbose=args.verbose)
        
        print()
        print("-" * 40)
        valid_count = sum(1 for r in results if r.valid)
        print(f"Total: {len(results)} | Valid: {valid_count} | Invalid: {len(results) - valid_count}")
        
        if args.strict:
            print("(Strict mode: warnings treated as errors)")
    
    # Exit code
    if any(not r.valid for r in results):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
