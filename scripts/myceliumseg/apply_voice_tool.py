"""
Apply run_myceliumseg_validation to voice_tools_api.py. Run from repo root.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_API = REPO_ROOT / "mycosoft_mas" / "core" / "routers" / "voice_tools_api.py"

def main():
    text = VOICE_API.read_text(encoding="utf-8")

    # 1) Add "import re" and "import os" after "import logging"
    if "import re\n" not in text:
        text = text.replace("import logging\n", "import logging\nimport os\nimport re\n")

    # 2) Add branch in execute_tool
    old_branch = '        elif tool_name == "system_status":\n            return await _get_system_status(query)\n        else:'
    new_branch = '''        elif tool_name == "system_status":
            return await _get_system_status(query)
        elif tool_name == "run_myceliumseg_validation":
            return await _run_myceliumseg_validation(query)
        else:'''
    if "run_myceliumseg_validation" not in text:
        text = text.replace(old_branch, new_branch)

    # 3) Add handler before "# Direct device status"
    marker = "\n# Direct device status endpoint"
    handler = '''
async def _run_myceliumseg_validation(query: str) -> ToolCallResponse:
    """Run MyceliumSeg validation experiment (Petri dish / segmentation metrics). Full automation, minimal input."""
    base_url = os.getenv("MYCELIUMSEG_API_URL", "http://localhost:8010/mindex/myceliumseg").rstrip("/")
    limit = 5
    match = re.search(r"\\b(\\d+)\\s*(?:samples?|images?)?\\b", query, re.I) or re.search(r"limit\\s*(\\d+)", query, re.I)
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
    if "_run_myceliumseg_validation" not in text:
        text = text.replace(marker, handler + marker)

    VOICE_API.write_text(text, encoding="utf-8")
    print("Patched", VOICE_API)


if __name__ == "__main__":
    main()
