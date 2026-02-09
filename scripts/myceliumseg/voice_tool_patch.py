# Patch for mycosoft_mas/core/routers/voice_tools_api.py
# Add run_myceliumseg_validation tool. Apply by inserting the snippets below.

INSERT_IMPORT = '''
import re
import os
'''

# In execute_tool(), after "elif tool_name == \"system_status\":" add:
BRANCH = '''
        elif tool_name == "run_myceliumseg_validation":
            return await _run_myceliumseg_validation(query)
'''

# Add before "# Direct device status endpoint":
HANDLER = '''

async def _run_myceliumseg_validation(query: str) -> ToolCallResponse:
    """Run MyceliumSeg validation experiment (Petri dish / segmentation metrics). Full automation, minimal input."""
    base_url = os.getenv("MYCELIUMSEG_API_URL", "http://localhost:8010/mindex/myceliumseg").rstrip("/")
    limit = 5
    match = re.search(r"\\b(\\\\d+)\\s*(?:samples?|images?)?\\b", query, re.I) or re.search(r"limit\\s*(\\\\d+)", query, re.I)
    if match:
        limit = min(50, max(1, int(match.group(1))))
    try:
        import httpx
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{base_url}/validation/run", json={"dataset_slice": {"limit": limit}})
            r.raise_for_status()
            job = r.json()
    except Exception as e:
        logger.warning(f"MyceliumSeg validation request failed: {e}")
        return ToolCallResponse(
            success=False,
            tool_name="run_myceliumseg_validation",
            result=f"MyceliumSeg validation failed: {e}. Ensure the API is running at {base_url}.",
            data={"error": str(e)},
            timestamp=datetime.utcnow().isoformat()
        )
    status = job.get("status", "unknown")
    agg = job.get("aggregate") or {}
    if status == "completed" and agg:
        metrics = ", ".join(f"{k}: {v}" for k, v in list(agg.items())[:6])
        result = f"MyceliumSeg validation completed on {len(job.get('results', []))} samples. Metrics: {metrics}."
    elif status == "completed":
        result = f"MyceliumSeg validation completed. Job {job.get('id', '')}. No aggregate metrics."
    else:
        result = f"MyceliumSeg validation status: {status}. Job id: {job.get('id', '')}."
    return ToolCallResponse(
        success=(status == "completed"),
        tool_name="run_myceliumseg_validation",
        result=result,
        data={"job_id": job.get("id"), "status": status, "aggregate": agg, "results_count": len(job.get("results", []))},
        timestamp=datetime.utcnow().isoformat()
    )
'''
