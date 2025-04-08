import os
from datetime import datetime
from utils import log, save_lab_data, save_research_data, save_experiment, get_latest_experiments

async def handle_lab_task(data):
    task = data.get("msg", "")
    
    log(f"Received lab task: {task}")

    if "scrape" in task:
        # Placeholder for scraping logic
        research_data = {
            "title": "Sample Research Paper",
            "content": "Sample content for testing",
            "timestamp": datetime.utcnow(),
            "source": "test"
        }
        await save_research_data(research_data)
        return f"🧪 Scraped and saved latest fungal research data"
    
    elif "sensor" in task:
        # Placeholder for IoT hook
        sensor_data = {
            "sensor_id": "test_sensor",
            "value": 42.0,
            "timestamp": datetime.utcnow(),
            "type": "temperature"
        }
        await save_lab_data(sensor_data)
        return "🔬 Saved data from lab sensors"

    elif "experiment" in task:
        experiment = {
            "name": "Test Experiment",
            "description": "Testing MongoDB integration",
            "status": "running",
            "timestamp": datetime.utcnow()
        }
        await save_experiment(experiment)
        return "🧪 Created new experiment record"

    elif "status" in task:
        latest_experiments = await get_latest_experiments()
        return {
            "message": "Latest experiments retrieved",
            "experiments": latest_experiments
        }

    else:
        return f"Lab R&D agent received: {task}" 