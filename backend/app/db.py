"""Tiny SQLite persistence layer so agents/logs/chat survive restarts.

Kept deliberately small: a single connection guarded by a lock. Plenty for a
single-process dashboard. Swap for async/Postgres later if it ever needs to.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time

from .models import ActivityEvent, Agent, ChatMessage, LogLine

DB_PATH = os.environ.get("AGENT_DB", os.path.join(os.path.dirname(__file__), "..", "agents.db"))

FEED_LIMIT = 300  # how many recent activity events to retain / serve


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


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
                CREATE TABLE IF NOT EXISTS activity (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS usage_daily (
                    day TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_in INTEGER NOT NULL DEFAULT 0,
                    tokens_out INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (day, model)
                );
                CREATE INDEX IF NOT EXISTS idx_logs_agent ON logs(agent_id, ts);
                CREATE INDEX IF NOT EXISTS idx_msgs_agent ON messages(agent_id, ts);
                CREATE INDEX IF NOT EXISTS idx_activity_ts ON activity(ts);
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

    # ---- activity feed (global, cross-agent) ----
    def add_activity(self, ev: ActivityEvent) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO activity (id, data, ts) VALUES (?, ?, ?)",
                (ev.id, ev.model_dump_json(), ev.ts),
            )
            # keep the feed bounded
            self._conn.execute(
                "DELETE FROM activity WHERE id NOT IN "
                "(SELECT id FROM activity ORDER BY ts DESC LIMIT ?)",
                (FEED_LIMIT,),
            )
            self._conn.commit()

    def recent_activity(self, limit: int = FEED_LIMIT) -> list[ActivityEvent]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM activity ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ActivityEvent.model_validate_json(r["data"]) for r in rows]

    # ---- usage / cost ----
    def add_usage(self, model: str, tokens_in: int, tokens_out: int, cost: float, ts: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO usage_daily (day, model, tokens_in, tokens_out, cost) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(day, model) DO UPDATE SET "
                "tokens_in = tokens_in + excluded.tokens_in, "
                "tokens_out = tokens_out + excluded.tokens_out, "
                "cost = cost + excluded.cost",
                (_day(ts), model, tokens_in, tokens_out, cost),
            )
            self._conn.commit()

    def metrics(self, days: int = 14) -> dict:
        today = _day(time.time())
        with self._lock:
            total = self._conn.execute(
                "SELECT COALESCE(SUM(tokens_in),0) ti, COALESCE(SUM(tokens_out),0) to_, "
                "COALESCE(SUM(cost),0) c FROM usage_daily"
            ).fetchone()
            tday = self._conn.execute(
                "SELECT COALESCE(SUM(tokens_in),0) ti, COALESCE(SUM(tokens_out),0) to_, "
                "COALESCE(SUM(cost),0) c FROM usage_daily WHERE day=?",
                (today,),
            ).fetchone()
            by_model = self._conn.execute(
                "SELECT model, SUM(tokens_in) ti, SUM(tokens_out) to_, SUM(cost) c "
                "FROM usage_daily GROUP BY model ORDER BY c DESC"
            ).fetchall()
            daily = self._conn.execute(
                "SELECT day, SUM(tokens_in) ti, SUM(tokens_out) to_, SUM(cost) c "
                "FROM usage_daily GROUP BY day ORDER BY day DESC LIMIT ?",
                (days,),
            ).fetchall()
        return {
            "total": {"tokens_in": total["ti"], "tokens_out": total["to_"], "cost": total["c"]},
            "today": {"tokens_in": tday["ti"], "tokens_out": tday["to_"], "cost": tday["c"]},
            "by_model": [
                {"model": r["model"], "tokens_in": r["ti"], "tokens_out": r["to_"], "cost": r["c"]}
                for r in by_model
            ],
            "daily": [
                {"day": r["day"], "tokens_in": r["ti"], "tokens_out": r["to_"], "cost": r["c"]}
                for r in reversed(daily)
            ],
        }

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
