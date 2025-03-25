import os
from utils import log

async def handle_lab_task(data):
    task = data.get("msg", "")
    
    # You'll replace this with actual lab actions
    log(f"Received lab task: {task}")

    if "scrape" in task:
        # Placeholder for scraping logic
        return f"🧪 Scraping latest fungal data for task: {task}"
    
    elif "sensor" in task:
        # Placeholder for IoT hook
        return "🔬 Reading data from lab sensors..."

    else:
        return f"Lab R&D agent received: {task}" 