# Agent Control Panel

A dashboard to **deploy, track, and chat with Claude-style agents**. Spin up an
agent, give it a task in chat, and watch its activity stream live — status,
progress, tool calls, and replies — all from one mission-control view.

> **Status:** v1 runs on a **mock agent runner** so the full dashboard works
> end-to-end today. Swapping in the real [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)
> is a single-file change (`backend/app/runner.py`) — nothing else has to move.

## Architecture

```
React dashboard ──REST (spawn / chat / stop)──▶ FastAPI backend
       ▲                                              │
       └────────── WebSocket (live feed) ─────────────┘
                                                   AgentManager ─▶ Runner (mock today,
                                                        │            Agent SDK later)
                                                        └─▶ SQLite (history)
```

- **`backend/app/runner.py`** — the seam. `Runner.run(prompt, emit)` streams
  logs/messages back. `MockRunner` fakes the work today.
- **`backend/app/manager.py`** — agent state, orchestration, WebSocket fan-out.
- **`backend/app/main.py`** — REST + `/ws` endpoints.
- **`frontend/`** — React (Vite). Sidebar of agents, per-agent chat + live log stream.

## Run it

```bash
./scripts/dev.sh
```

Then open the dashboard at **http://localhost:5173** (API on `:8000`).

Or run the two halves manually:

```bash
# backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend && npm install && npm run dev
```

## API

| Method | Path                         | Purpose                          |
|--------|------------------------------|----------------------------------|
| GET    | `/api/agents`                | List agents                      |
| POST   | `/api/agents`                | Create an agent `{name, role}`   |
| GET    | `/api/agents/{id}`           | Agent + its logs + chat history  |
| POST   | `/api/agents/{id}/chat`      | Send a prompt → agent goes to work |
| POST   | `/api/agents/{id}/stop`      | Stop a running agent             |
| DELETE | `/api/agents/{id}`           | Remove an agent                  |
| WS     | `/ws`                        | Live snapshot + event stream     |

## Going real (next step)

Implement `Runner.run` in `backend/app/runner.py` with the Claude Agent SDK,
forwarding each SDK message / tool call through the same `emit(...)` callback.
Set `ANTHROPIC_API_KEY` and point `get_runner()` at the new class — the
dashboard already knows how to render everything it emits.
