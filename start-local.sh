#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[start-local] Missing required command: $1"
    exit 1
  fi
}

port_in_use() {
  lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

ensure_port_free() {
  local port=$1
  local name=$2
  if port_in_use "${port}"; then
    echo "[start-local] ${name} port ${port} is already in use. Stop the existing process first."
    exit 1
  fi
}

cleanup() {
  local exit_code=$?
  if [[ -n "${PROXY_PID:-}" ]]; then kill "${PROXY_PID}" >/dev/null 2>&1 || true; fi
  if [[ -n "${AGENT_PID:-}" ]]; then kill "${AGENT_PID}" >/dev/null 2>&1 || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "${FRONTEND_PID}" >/dev/null 2>&1 || true; fi
  wait >/dev/null 2>&1 || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

require_command uv
require_command npm

cd "${ROOT_DIR}"

ensure_port_free 8000 "Proxy"
ensure_port_free 8002 "Agent"
ensure_port_free 3000 "Frontend"

SQLITE_PATH="${AGENT_FIREWALL_SQLITE_PATH:-${HOME}/.openclaw/agent-firewall.sqlite}"
mkdir -p "$(dirname "${SQLITE_PATH}")"

export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///${SQLITE_PATH}}"
export CACHE_BACKEND="${CACHE_BACKEND:-memory}"
export REDIS_URL="${REDIS_URL:-}"
export ENABLE_LANGFUSE="${ENABLE_LANGFUSE:-false}"

echo "[start-local] Starting local application services..."
echo "[start-local] SQLite:   ${SQLITE_PATH}"
echo "[start-local] Cache:    ${CACHE_BACKEND}"
echo "[start-local] Langfuse: ${ENABLE_LANGFUSE}"
(cd apps/proxy-service && uv run python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000) &
PROXY_PID=$!

(cd apps/agent && uv run python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8002) &
AGENT_PID=$!

(cd apps/frontend && npm run dev) &
FRONTEND_PID=$!

echo "[start-local] Frontend:  http://localhost:3000"
echo "[start-local] Proxy:     http://localhost:8000"
echo "[start-local] Agent:     http://localhost:8002"
echo "[start-local] Press Ctrl+C to stop local processes."

wait
