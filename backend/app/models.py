"""Pydantic schemas shared across the API and the agent runner."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> float:
    return time.time()


class AgentStatus(str, Enum):
    idle = "idle"          # created, no task yet
    queued = "queued"      # task accepted, about to start
    running = "running"    # actively working
    completed = "completed"  # finished its task successfully
    failed = "failed"      # task errored out
    stopped = "stopped"    # stopped by the user


class LogLevel(str, Enum):
    info = "info"
    tool = "tool"
    success = "success"
    error = "error"


class LogLine(BaseModel):
    id: str = Field(default_factory=_id)
    ts: float = Field(default_factory=_now)
    level: LogLevel = LogLevel.info
    text: str
    # When the line represents a tool call, these enrich the execution timeline.
    tool: Optional[str] = None       # tool name, e.g. "edit_file"
    dur_ms: Optional[int] = None     # how long the tool call took


class ChatMessage(BaseModel):
    id: str = Field(default_factory=_id)
    ts: float = Field(default_factory=_now)
    role: Literal["user", "agent", "system"]
    content: str


class ActivityEvent(BaseModel):
    """One entry in the global, cross-agent live feed."""

    id: str = Field(default_factory=_id)
    ts: float = Field(default_factory=_now)
    agent_id: str
    agent_name: str
    kind: Literal["status", "tool", "message", "error"] = "status"
    level: LogLevel = LogLevel.info
    text: str


class Agent(BaseModel):
    # `model` is a normal field name here; opt out of pydantic's protected ns.
    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=_id)
    name: str
    role: str = "general"          # what kind of work it does
    model: str = "claude-sonnet-4-6"  # llm powering this agent
    status: AgentStatus = AgentStatus.idle
    task: Optional[str] = None      # current/last task prompt
    created_at: float = Field(default_factory=_now)
    updated_at: float = Field(default_factory=_now)
    last_beat: float = Field(default_factory=_now)  # heartbeat for health view
    progress: int = 0               # 0-100, rough completion of current task
    last_activity: Optional[str] = None  # latest log line, for at-a-glance views
    # cumulative usage across everything this agent has done
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tasks_done: int = 0


# ---- request bodies ----

class CreateAgent(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    role: str = "general"
    model: str = "claude-sonnet-4-6"


class Prompt(BaseModel):
    content: str
