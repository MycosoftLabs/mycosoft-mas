from fastapi import FastAPI, Request
from agent import handle_lab_task

app = FastAPI()

@app.post("/task")
async def receive_task(req: Request):
    data = await req.json()
    response = await handle_lab_task(data)
    return {"result": response} 