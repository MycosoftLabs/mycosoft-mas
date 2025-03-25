from utils import log

async def handle_dev_task(data):
    task = data.get("msg", "")

    log(f"Received dev task: {task}")

    if "lint" in task:
        return "🧼 Running linter on latest repo code..."

    elif "test" in task:
        return "🧪 Running test suite for MAS..."

    elif "deploy" in task:
        return "🚀 Triggering deployment pipeline..."

    else:
        return f"Dev Agent received: {task}" 