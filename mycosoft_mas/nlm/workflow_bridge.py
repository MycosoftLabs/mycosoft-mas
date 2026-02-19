"""
NLM-to-Workflow Bridge - February 18, 2026

Connects NLM inference outputs to n8n workflows.
Trigger conditions (e.g. confidence threshold, prediction type) map to workflow execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default confidence threshold above which we may trigger workflows
DEFAULT_CONFIDENCE_THRESHOLD = 0.85

# Map NLM query/prediction types or labels to workflow names (by name or webhook path)
# Add workflow names that exist in n8n/workflows/ or on the n8n instance.
NLM_TO_WORKFLOW_MAP = {
    "anomaly": "security_alert",
    "anomaly_detection": "security_alert",
    "security_alert": "security_alert",
    "spore_forecast": "earth2_spore_alert",
    "earth2": "earth2_spore_alert",
    "model_drift": "nlm_model_hub",
    "species_id": "mindex_species_scraper",
    "species_identification": "mindex_species_scraper",
    "taxonomy": "mindex_species_scraper",
}


def get_workflow_for_prediction(
    query_type: str,
    labels: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Resolve workflow name from NLM prediction type and optional labels/metadata.
    Returns workflow name if a mapping exists, else None.
    """
    labels = labels or []
    q = (query_type or "").lower()
    for key, wf in NLM_TO_WORKFLOW_MAP.items():
        if key in q or any(key in (l or "").lower() for l in labels):
            return wf
    if metadata:
        trigger = (metadata.get("trigger_workflow") or metadata.get("workflow") or "").strip()
        if trigger:
            return trigger
    return None


async def trigger_workflow_from_nlm(
    workflow_name: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Trigger an n8n workflow with NLM results as input data.
    Uses N8NWorkflowAgent.process_task(type=execute_workflow).
    """
    try:
        from mycosoft_mas.agents.workflow.n8n_workflow_agent import N8NWorkflowAgent
        agent = N8NWorkflowAgent(agent_id="nlm-bridge", name="N8N Workflow", config={})
        result = await agent.process_task({
            "type": "execute_workflow",
            "workflow_name": workflow_name,
            "data": input_data,
        })
        return result
    except Exception as e:
        logger.warning("NLM workflow trigger failed for %s: %s", workflow_name, e)
        return {"status": "error", "message": str(e)}


async def maybe_trigger_workflow_from_prediction(
    query_type: str,
    confidence: float,
    prediction_result: Dict[str, Any],
    labels: Optional[List[str]] = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> Optional[Dict[str, Any]]:
    """
    If confidence meets threshold and mapping exists, trigger the corresponding workflow.
    Returns workflow execution result or None if no trigger.
    """
    if confidence < confidence_threshold:
        return None
    workflow_name = get_workflow_for_prediction(
        query_type,
        labels=labels,
        metadata=prediction_result.get("metadata"),
    )
    if not workflow_name:
        return None
    input_data = {
        "nlm_query_type": query_type,
        "nlm_confidence": confidence,
        "prediction": prediction_result,
    }
    return await trigger_workflow_from_nlm(workflow_name, input_data)
