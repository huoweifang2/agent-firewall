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

require_command docker
require_command uv
require_command npm

if ! docker info >/dev/null 2>&1; then
  echo "[start-local] Docker daemon is not running. Start Docker Desktop first."
  exit 1
fi

cd "${ROOT_DIR}/infra"
docker compose up db langfuse -d

if port_in_use 6379; then
  echo "[start-local] Port 6379 already in use. Reusing the existing Redis instance."
else
  docker compose up redis -d
fi

cd "${ROOT_DIR}"

ensure_port_free 8000 "Proxy"
ensure_port_free 8002 "Agent"
ensure_port_free 3000 "Frontend"

echo "[start-local] Starting local application services..."
(cd apps/proxy-service && uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000) &
PROXY_PID=$!

(cd apps/agent && uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8002) &
AGENT_PID=$!

(cd apps/frontend && npm run dev) &
FRONTEND_PID=$!

echo "[start-local] Frontend:  http://localhost:3000"
echo "[start-local] Proxy:     http://localhost:8000"
echo "[start-local] Agent:     http://localhost:8002"
echo "[start-local] Langfuse:  http://localhost:3001"
echo "[start-local] Press Ctrl+C to stop local processes."

wait
