from fastapi import FastAPI, Request
from orchestrator import handle_task

app = FastAPI()

@app.post("/task")
async def receive_task(req: Request):
    data = await req.json()
    response = await handle_task(data)
    return {"result": response} 