"""FastAPI app: REST for control, WebSocket for the live feed."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .manager import AgentManager
from .models import CreateAgent, Prompt

app = FastAPI(title="Agent Control Panel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; lock down for production
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = AgentManager()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/agents")
async def list_agents():
    return [a.model_dump() for a in manager.list_agents()]


@app.get("/api/feed")
async def feed():
    return [e.model_dump() for e in manager.feed()]


@app.get("/api/metrics")
async def metrics():
    return manager.metrics()


@app.post("/api/agents", status_code=201)
async def create_agent(body: CreateAgent):
    agent = await manager.create(body)
    return agent.model_dump()


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = manager.get(agent_id)
    if agent is None:
        raise HTTPException(404, "agent not found")
    return {
        "agent": agent.model_dump(),
        "logs": [l.model_dump() for l in manager.logs(agent_id)],
        "messages": [m.model_dump() for m in manager.messages(agent_id)],
    }


@app.delete("/api/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    if not await manager.delete(agent_id):
        raise HTTPException(404, "agent not found")


@app.post("/api/agents/{agent_id}/chat")
async def chat(agent_id: str, body: Prompt):
    """Send a prompt to an agent. This is what makes the agent go to work."""
    agent = await manager.deploy(agent_id, body.content)
    if agent is None:
        raise HTTPException(404, "agent not found")
    return agent.model_dump()


@app.post("/api/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    if manager.get(agent_id) is None:
        raise HTTPException(404, "agent not found")
    await manager.stop(agent_id)
    return manager.get(agent_id).model_dump()


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await manager.conns.connect(websocket)
    try:
        # send a snapshot so a fresh dashboard is immediately in sync
        await websocket.send_json(
            {
                "type": "snapshot",
                "agents": [a.model_dump() for a in manager.list_agents()],
                "feed": [e.model_dump() for e in manager.feed()],
                "metrics": manager.metrics(),
            }
        )
        while True:
            await websocket.receive_text()  # keep-alive; we don't expect client msgs
    except WebSocketDisconnect:
        await manager.conns.disconnect(websocket)
    except Exception:
        await manager.conns.disconnect(websocket)
