#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Vite) together for local development.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- backend ---
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACK=$!

# --- frontend ---
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null' EXIT
echo "Backend: http://localhost:8000  |  Dashboard: http://localhost:5173"
wait
