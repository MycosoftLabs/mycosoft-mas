import httpx
from agents_config import AGENTS

async def handle_task(data):
    task_type = data.get("type")
    payload = data.get("payload", {})
    
    # Basic routing logic
    agent = AGENTS.get(task_type)
    if not agent:
        return f"No agent configured for task: {task_type}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(agent["endpoint"], json=payload)
            return resp.json()
    except Exception as e:
        return {"error": str(e)} 