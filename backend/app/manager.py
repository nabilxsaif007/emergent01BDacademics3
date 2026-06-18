"""Owns agent state, the live WebSocket fan-out, and task orchestration."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from .db import Store
from .models import (
    Agent,
    AgentStatus,
    ChatMessage,
    CreateAgent,
    LogLevel,
    LogLine,
)
from .runner import get_runner


class ConnectionManager:
    """Tracks connected dashboards and broadcasts events to all of them."""

    def __init__(self) -> None:
        self._conns: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._conns.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._conns.discard(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._conns)
        dead = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._conns.discard(ws)


class AgentManager:
    def __init__(self) -> None:
        self.store = Store()
        self.conns = ConnectionManager()
        self._agents: dict[str, Agent] = {a.id: a for a in self.store.all_agents()}
        self._tasks: dict[str, asyncio.Task] = {}
        # any agent left 'running' from a previous process is stale -> reset
        for a in self._agents.values():
            if a.status in (AgentStatus.running, AgentStatus.queued):
                a.status = AgentStatus.stopped
                self.store.save_agent(a)

    # ---- reads ----
    def list_agents(self) -> list[Agent]:
        return sorted(self._agents.values(), key=lambda a: a.created_at)

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def logs(self, agent_id: str) -> list[LogLine]:
        return self.store.logs_for(agent_id)

    def messages(self, agent_id: str) -> list[ChatMessage]:
        return self.store.messages_for(agent_id)

    # ---- writes ----
    async def create(self, body: CreateAgent) -> Agent:
        agent = Agent(name=body.name, role=body.role)
        self._agents[agent.id] = agent
        self.store.save_agent(agent)
        await self.conns.broadcast({"type": "agent_created", "agent": agent.model_dump()})
        return agent

    async def delete(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        await self.stop(agent_id)
        del self._agents[agent_id]
        self.store.delete_agent(agent_id)
        await self.conns.broadcast({"type": "agent_deleted", "agent_id": agent_id})
        return True

    async def stop(self, agent_id: str) -> None:
        task = self._tasks.pop(agent_id, None)
        if task and not task.done():
            task.cancel()
        agent = self._agents.get(agent_id)
        if agent and agent.status in (AgentStatus.running, AgentStatus.queued):
            await self._set_status(agent, AgentStatus.stopped)

    async def deploy(self, agent_id: str, prompt: str) -> Agent | None:
        """Assign a task to an agent and start it running (used by chat too)."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        if agent_id in self._tasks and not self._tasks[agent_id].done():
            # already busy; ignore (UI disables send while running)
            return agent

        agent.task = prompt
        await self._add_message(agent, ChatMessage(role="user", content=prompt))
        await self._set_status(agent, AgentStatus.queued, progress=0)
        self._tasks[agent_id] = asyncio.create_task(self._run(agent, prompt))
        return agent

    # ---- internals ----
    async def _run(self, agent: Agent, prompt: str) -> None:
        runner = get_runner()
        await self._set_status(agent, AgentStatus.running)

        async def emit(kind: str, payload: object) -> None:
            if kind == "log":
                await self._add_log(agent, payload)  # type: ignore[arg-type]
            elif kind == "message":
                await self._add_message(agent, payload)  # type: ignore[arg-type]
            elif kind == "progress":
                agent.progress = int(payload)  # type: ignore[arg-type]
                await self._touch(agent)

        try:
            await runner.run(prompt, emit)
            await self._set_status(agent, AgentStatus.completed, progress=100)
        except asyncio.CancelledError:
            await self._set_status(agent, AgentStatus.stopped)
            raise
        except Exception as exc:  # noqa: BLE001 - surface any runner failure
            await self._add_log(agent, LogLine(level=LogLevel.error, text=str(exc)))
            await self._set_status(agent, AgentStatus.failed)
        finally:
            self._tasks.pop(agent.id, None)

    async def _set_status(self, agent: Agent, status: AgentStatus, progress: int | None = None) -> None:
        agent.status = status
        if progress is not None:
            agent.progress = progress
        await self._touch(agent)

    async def _touch(self, agent: Agent) -> None:
        import time

        agent.updated_at = time.time()
        self.store.save_agent(agent)
        await self.conns.broadcast({"type": "agent_updated", "agent": agent.model_dump()})

    async def _add_log(self, agent: Agent, line: LogLine) -> None:
        self.store.add_log(agent.id, line)
        await self.conns.broadcast(
            {"type": "log", "agent_id": agent.id, "line": line.model_dump()}
        )
        # surface the latest line on the agent row for the fleet overview
        agent.last_activity = line.text
        await self._touch(agent)

    async def _add_message(self, agent: Agent, msg: ChatMessage) -> None:
        self.store.add_message(agent.id, msg)
        await self.conns.broadcast(
            {"type": "message", "agent_id": agent.id, "message": msg.model_dump()}
        )
