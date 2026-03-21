"""
Legal Compliance Agent for Mycosoft MAS

This module implements the LegalComplianceAgent that handles legal compliance,
regulatory requirements, and corporate governance rules.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from mycosoft_mas.agents.base_agent import BaseAgent


class LegalComplianceAgent(BaseAgent):
    """
    Agent that handles legal compliance for Mycosoft Inc.

    This agent manages:
    - Corporate compliance monitoring
    - Regulatory requirement tracking
    - Document retention policies
    - Corporate governance rules enforcement
    """

    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the legal compliance agent."""
        super().__init__(agent_id, name, config)

        # Load configuration
        self.compliance_config = config.get("compliance", {})
        self.retention_config = config.get("retention", {})

        # Initialize state
        self.compliance_rules = {}
        self.regulatory_requirements = {}
        self.retention_policies = {}
        self.compliance_checks = {}

        # Create data directory
        self.data_dir = Path("data/legal")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.metrics.update(
            {
                "compliance_checks": 0,
                "violations_detected": 0,
                "documents_archived": 0,
                "policies_updated": 0,
            }
        )

    async def _initialize_services(self) -> None:
        """Initialize legal compliance services."""
        # Load compliance rules
        await self._load_compliance_rules()

        # Load regulatory requirements
        await self._load_regulatory_requirements()

        # Initialize retention policies
        await self._initialize_retention_policies()

    async def _load_compliance_rules(self) -> None:
        """Load corporate compliance rules."""
        rules_file = self.data_dir / "compliance_rules.json"
        self.compliance_rules = await self._load_json_file(rules_file, default={})

    async def _load_regulatory_requirements(self) -> None:
        """Load regulatory requirements."""
        requirements_file = self.data_dir / "regulatory_requirements.json"
        self.regulatory_requirements = await self._load_json_file(requirements_file, default={})

    async def _initialize_retention_policies(self) -> None:
        """Initialize document retention policies."""
        policies_file = self.data_dir / "retention_policies.json"
        self.retention_policies = await self._load_json_file(policies_file, default={})

    async def check_compliance(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check compliance of an entity against rules and requirements.

        Args:
            entity: Entity to check for compliance

        Returns:
            Dict[str, Any]: Compliance check results
        """
        try:
            # Validate entity
            if not self._validate_entity(entity):
                raise ValueError("Invalid entity format")

            # Perform compliance check
            results = await self._perform_compliance_check(entity)

            # Record check results
            await self._record_compliance_check(entity, results)

            # Update metrics
            self.metrics["compliance_checks"] += 1
            if results.get("violations", []):
                self.metrics["violations_detected"] += 1

            return results
        except Exception as e:
            self.logger.error(f"Failed to check compliance: {str(e)}")
            return {"error": str(e)}

    async def archive_document(self, document: Dict[str, Any]) -> bool:
        """
        Archive a document according to retention policies.

        Args:
            document: Document to archive

        Returns:
            bool: True if document was archived successfully
        """
        try:
            # Validate document
            if not self._validate_document(document):
                raise ValueError("Invalid document format")

            # Determine retention policy
            policy = await self._determine_retention_policy(document)

            # Archive document
            await self._archive_document(document, policy)

            # Update metrics
            self.metrics["documents_archived"] += 1

            return True
        except Exception as e:
            self.logger.error(f"Failed to archive document: {str(e)}")
            return False

    async def update_compliance_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Update a compliance policy.

        Args:
            policy: Updated policy details

        Returns:
            bool: True if policy was updated successfully
        """
        try:
            # Validate policy
            if not self._validate_policy(policy):
                raise ValueError("Invalid policy format")

            # Update policy
            await self._update_policy(policy)

            # Notify relevant parties
            await self._notify_policy_update(policy)

            # Update metrics
            self.metrics["policies_updated"] += 1

            return True
        except Exception as e:
            self.logger.error(f"Failed to update compliance policy: {str(e)}")
            return False

    async def check_regulatory_compliance(self, requirement_id: str) -> Dict[str, Any]:
        """
        Check compliance with a specific regulatory requirement.

        Args:
            requirement_id: ID of the regulatory requirement to check

        Returns:
            Dict[str, Any]: Compliance check results
        """
        try:
            # Get requirement details
            requirement = await self._get_requirement(requirement_id)

            # Check compliance
            results = await self._check_requirement_compliance(requirement)

            # Record results
            await self._record_requirement_check(requirement_id, results)

            return results
        except Exception as e:
            self.logger.error(f"Failed to check regulatory compliance: {str(e)}")
            return {"error": str(e)}

    def _validate_entity(self, entity: Dict[str, Any]) -> bool:
        """Validate entity format."""
        required_fields = ["type", "id", "data"]
        return all(field in entity for field in required_fields)

    def _validate_document(self, document: Dict[str, Any]) -> bool:
        """Validate document format."""
        required_fields = ["id", "type", "content", "metadata"]
        return all(field in document for field in required_fields)

    def _validate_policy(self, policy: Dict[str, Any]) -> bool:
        """Validate policy format."""
        required_fields = ["id", "type", "rules", "effective_date"]
        return all(field in policy for field in required_fields)

    async def _load_json_file(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.logger.error("Failed to read %s: %s", path, exc)
            return default

    async def _write_json_file(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    async def _perform_compliance_check(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Perform compliance check on an entity."""
        entity_type = entity.get("type")
        rules = self.compliance_rules.get(entity_type, [])
        if not rules:
            return {
                "status": "no_rules_configured",
                "entity_id": entity.get("id"),
                "entity_type": entity_type,
                "violations": [],
                "checked_at": datetime.now().isoformat(),
            }

        violations = []
        entity_data = entity.get("data", {})
        for rule in rules:
            required_fields = rule.get("required_fields", [])
            missing = [field for field in required_fields if field not in entity_data]
            if missing:
                violations.append(
                    {
                        "rule_id": rule.get("id"),
                        "type": "missing_fields",
                        "details": missing,
                    }
                )
            disallowed = rule.get("disallowed_fields", [])
            present = [field for field in disallowed if field in entity_data]
            if present:
                violations.append(
                    {
                        "rule_id": rule.get("id"),
                        "type": "disallowed_fields",
                        "details": present,
                    }
                )

        status = "compliant" if not violations else "violations_detected"
        return {
            "status": status,
            "entity_id": entity.get("id"),
            "entity_type": entity_type,
            "violations": violations,
            "checked_at": datetime.now().isoformat(),
        }

    async def _record_compliance_check(
        self, entity: Dict[str, Any], results: Dict[str, Any]
    ) -> None:
        """Record results of a compliance check."""
        checks_file = self.data_dir / "compliance_checks.json"
        current = await self._load_json_file(checks_file, default=[])
        current.append(
            {
                "entity_id": entity.get("id"),
                "entity_type": entity.get("type"),
                "results": results,
                "recorded_at": datetime.now().isoformat(),
            }
        )
        await self._write_json_file(checks_file, current)

    async def _determine_retention_policy(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Determine retention policy for a document."""
        doc_type = document.get("type")
        policy = self.retention_policies.get(doc_type)
        if not policy:
            default_id = self.retention_config.get("default_policy_id")
            policy = self.retention_policies.get(default_id) if default_id else None
        if not policy:
            raise ValueError(f"No retention policy configured for document type {doc_type}")
        return policy

    async def _archive_document(self, document: Dict[str, Any], policy: Dict[str, Any]) -> None:
        """Archive a document according to retention policy."""
        archive_dir = self.data_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_id = f"{document.get('id')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        archive_path = archive_dir / f"{archive_id}.json"
        payload = {
            "document": document,
            "policy": policy,
            "archived_at": datetime.now().isoformat(),
        }
        await self._write_json_file(archive_path, payload)

    async def _update_policy(self, policy: Dict[str, Any]) -> None:
        """Update a compliance policy."""
        policy_type = policy.get("type")
        if policy_type == "retention":
            self.retention_policies[policy["id"]] = policy
            await self._write_json_file(
                self.data_dir / "retention_policies.json", self.retention_policies
            )
        else:
            entity_type = policy.get("entity_type", "default")
            self.compliance_rules.setdefault(entity_type, [])
            updated = [p for p in self.compliance_rules[entity_type] if p.get("id") != policy["id"]]
            updated.append(policy)
            self.compliance_rules[entity_type] = updated
            await self._write_json_file(
                self.data_dir / "compliance_rules.json", self.compliance_rules
            )

    async def _notify_policy_update(self, policy: Dict[str, Any]) -> None:
        """Notify relevant parties about policy update."""
        updates_file = self.data_dir / "policy_updates.json"
        current = await self._load_json_file(updates_file, default=[])
        current.append(
            {
                "policy_id": policy.get("id"),
                "policy_type": policy.get("type"),
                "effective_date": policy.get("effective_date"),
                "notified_at": datetime.now().isoformat(),
            }
        )
        await self._write_json_file(updates_file, current)
        self.logger.info("Policy update recorded for %s", policy.get("id"))

    async def _get_requirement(self, requirement_id: str) -> Dict[str, Any]:
        """Get details of a regulatory requirement."""
        requirement = self.regulatory_requirements.get(requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        return requirement

    async def _check_requirement_compliance(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with a regulatory requirement."""
        checks = requirement.get("checks", [])
        if not checks:
            return {
                "status": "no_checks_configured",
                "requirement_id": requirement.get("id"),
                "checked_at": datetime.now().isoformat(),
                "violations": [],
            }

        violations = []
        requirement_data = requirement.get("data", {})
        for check in checks:
            required_fields = check.get("required_fields", [])
            missing = [field for field in required_fields if field not in requirement_data]
            if missing:
                violations.append(
                    {
                        "check_id": check.get("id"),
                        "type": "missing_fields",
                        "details": missing,
                    }
                )

        status = "compliant" if not violations else "violations_detected"
        return {
            "status": status,
            "requirement_id": requirement.get("id"),
            "checked_at": datetime.now().isoformat(),
            "violations": violations,
        }

    async def _record_requirement_check(self, requirement_id: str, results: Dict[str, Any]) -> None:
        """Record results of a regulatory requirement check."""
        checks_file = self.data_dir / "requirement_checks.json"
        current = await self._load_json_file(checks_file, default=[])
        current.append(
            {
                "requirement_id": requirement_id,
                "results": results,
                "recorded_at": datetime.now().isoformat(),
            }
        )
        await self._write_json_file(checks_file, current)
