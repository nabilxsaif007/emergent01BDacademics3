"""Pydantic schemas shared across the API and the agent runner."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class ChatMessage(BaseModel):
    id: str = Field(default_factory=_id)
    ts: float = Field(default_factory=_now)
    role: Literal["user", "agent", "system"]
    content: str


class Agent(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    role: str = "general"          # what kind of work it does
    status: AgentStatus = AgentStatus.idle
    task: Optional[str] = None      # current/last task prompt
    created_at: float = Field(default_factory=_now)
    updated_at: float = Field(default_factory=_now)
    progress: int = 0               # 0-100, rough completion of current task
    last_activity: Optional[str] = None  # latest log line, for at-a-glance views


# ---- request bodies ----

class CreateAgent(BaseModel):
    name: str
    role: str = "general"


class Prompt(BaseModel):
    content: str
