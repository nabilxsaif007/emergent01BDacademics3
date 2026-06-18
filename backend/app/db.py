"""Tiny SQLite persistence layer so agents/logs/chat survive restarts.

Kept deliberately small: a single connection guarded by a lock. Plenty for a
single-process dashboard. Swap for async/Postgres later if it ever needs to.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any

from .models import Agent, ChatMessage, LogLine

DB_PATH = os.environ.get("AGENT_DB", os.path.join(os.path.dirname(__file__), "..", "agents.db"))


class Store:
    def __init__(self, path: str = DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_logs_agent ON logs(agent_id, ts);
                CREATE INDEX IF NOT EXISTS idx_msgs_agent ON messages(agent_id, ts);
                """
            )
            self._conn.commit()

    # ---- agents ----
    def save_agent(self, agent: Agent) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO agents (id, data, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (agent.id, agent.model_dump_json(), agent.created_at),
            )
            self._conn.commit()

    def delete_agent(self, agent_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM agents WHERE id=?", (agent_id,))
            self._conn.execute("DELETE FROM logs WHERE agent_id=?", (agent_id,))
            self._conn.execute("DELETE FROM messages WHERE agent_id=?", (agent_id,))
            self._conn.commit()

    def all_agents(self) -> list[Agent]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM agents ORDER BY created_at ASC"
            ).fetchall()
        return [Agent.model_validate_json(r["data"]) for r in rows]

    # ---- logs ----
    def add_log(self, agent_id: str, line: LogLine) -> None:
        self._add("logs", agent_id, line.id, line.model_dump_json(), line.ts)

    def logs_for(self, agent_id: str) -> list[LogLine]:
        return [LogLine.model_validate_json(d) for d in self._list("logs", agent_id)]

    # ---- messages ----
    def add_message(self, agent_id: str, msg: ChatMessage) -> None:
        self._add("messages", agent_id, msg.id, msg.model_dump_json(), msg.ts)

    def messages_for(self, agent_id: str) -> list[ChatMessage]:
        return [ChatMessage.model_validate_json(d) for d in self._list("messages", agent_id)]

    # ---- helpers ----
    def _add(self, table: str, agent_id: str, row_id: str, data: str, ts: float) -> None:
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO {table} (id, agent_id, data, ts) VALUES (?, ?, ?, ?)",
                (row_id, agent_id, data, ts),
            )
            self._conn.commit()

    def _list(self, table: str, agent_id: str) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT data FROM {table} WHERE agent_id=? ORDER BY ts ASC", (agent_id,)
            ).fetchall()
        return [r["data"] for r in rows]
