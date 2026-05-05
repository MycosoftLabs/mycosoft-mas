"""Twenty archetype harness classes — specialized cycles extend DefaultAgent100."""

from __future__ import annotations

from mycosoft_mas.agent100.base_agent100 import BaseAgent100
from mycosoft_mas.agent100.types import AgentRow, CallRecord


class DefaultAgent100(BaseAgent100):
    """Health + optional single Worldview GET from row.meta['worldview_path']."""

    def run_cycle(self, mode: str) -> list[CallRecord]:
        recs: list[CallRecord] = [self.ping_worldview_health()]
        path = self.row.meta.get("worldview_path") if isinstance(self.row.meta, dict) else None
        if isinstance(path, str) and path.strip():
            status, _data, ms = self._wv.get(path.strip())
            recs.append(
                CallRecord(
                    agent_id=self.row.id,
                    archetype=self.row.archetype,
                    framework=self.row.framework,
                    dataset_id=self.row.meta.get("dataset_id") if isinstance(self.row.meta, dict) else None,
                    mode=mode,
                    request_path=path.strip(),
                    status_code=status,
                    latency_ms=int(ms),
                    cache=None,
                    cost_debited=None,
                    rate_weight=None,
                    bytes=None,
                    schema_valid=None,
                    freshness_ok=status == 200,
                    error_class=None if status == 200 else f"http_{status}",
                    request_id=None,
                    envelope_ok=status == 200,
                )
            )
        return recs


class DefenseAnalystAgent(DefaultAgent100):
    pass


class FinanceOpsAgent(DefaultAgent100):
    pass


class ScientificResearcherAgent(DefaultAgent100):
    pass


class DeviceFieldTechAgent(DefaultAgent100):
    pass


class DataEngineerAgent(DefaultAgent100):
    pass


class ProductManagerAgent(DefaultAgent100):
    pass


class SecurityAuditorAgent(DefaultAgent100):
    pass


class LegalComplianceAgent(DefaultAgent100):
    pass


class CustomerSuccessAgent(DefaultAgent100):
    pass


class ExecutiveAssistantAgent(DefaultAgent100):
    pass


class MarketingCreatorAgent(DefaultAgent100):
    pass


class SalesSdrAgent(DefaultAgent100):
    pass


class SupportTier1Agent(DefaultAgent100):
    pass


class DevopsSreAgent(DefaultAgent100):
    pass


class MlEngineerAgent(DefaultAgent100):
    pass


class BioinformaticsAgent(DefaultAgent100):
    pass


class GisRemoteSensingAgent(DefaultAgent100):
    pass


class SupplyChainAgent(DefaultAgent100):
    pass


class HrRecruiterAgent(DefaultAgent100):
    pass


class RandomStressAgent(DefaultAgent100):
    """Pentest-style stress archetype — use AGENT100_PENTEST_API_KEY in row.api_key_env."""

    pass


_ARCHETYPE_MAP: dict[str, type[BaseAgent100]] = {
    "defense_analyst": DefenseAnalystAgent,
    "finance_ops": FinanceOpsAgent,
    "scientific_researcher": ScientificResearcherAgent,
    "device_field_tech": DeviceFieldTechAgent,
    "data_engineer": DataEngineerAgent,
    "product_manager": ProductManagerAgent,
    "security_auditor": SecurityAuditorAgent,
    "legal_compliance": LegalComplianceAgent,
    "customer_success": CustomerSuccessAgent,
    "executive_assistant": ExecutiveAssistantAgent,
    "marketing_creator": MarketingCreatorAgent,
    "sales_sdr": SalesSdrAgent,
    "support_tier1": SupportTier1Agent,
    "devops_sre": DevopsSreAgent,
    "ml_engineer": MlEngineerAgent,
    "bioinformatics": BioinformaticsAgent,
    "gis_remote_sensing": GisRemoteSensingAgent,
    "supply_chain": SupplyChainAgent,
    "hr_recruiter": HrRecruiterAgent,
    "random_stress": RandomStressAgent,
}


def archetype_handler_for(archetype: str) -> type[BaseAgent100]:
    return _ARCHETYPE_MAP.get(archetype, DefaultAgent100)
