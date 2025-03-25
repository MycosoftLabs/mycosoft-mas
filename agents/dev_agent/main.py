from fastapi import FastAPI, Request
from agent import handle_dev_task

app = FastAPI()

@app.post("/task")
async def receive_task(req: Request):
    data = await req.json()
    response = await handle_dev_task(data)
    return {"result": response} 