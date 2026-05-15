#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8012}"
FRONTEND_PORT="${FRONTEND_PORT:-3003}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
RUNTIME_CONFIG="${ROOT}/tmp/real-model-runtime-${BACKEND_PORT}.json"
DATABASE_URL="sqlite:///${ROOT}/tmp/real-model-${BACKEND_PORT}.db"

mkdir -p "${ROOT}/tmp"

cleanup_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" || true)"
  if [[ -n "${pids}" ]]; then
    kill ${pids} || true
  fi
}

cleanup_port "${BACKEND_PORT}"
cleanup_port "${FRONTEND_PORT}"

cd "${ROOT}/backend"
MODEL_PROVIDER=mlx \
MODEL_SWITCHING_ENABLED=true \
MODEL_RUNTIME_CONFIG_PATH="${RUNTIME_CONFIG}" \
DATABASE_URL="${DATABASE_URL}" \
CORS_ALLOW_ORIGIN_REGEX='https?://(localhost|127\.0\.0\.1|10\..*|192\.168\..*|100\..*|172\.(1[6-9]|2[0-9]|3[0-1])\..*)?(:[0-9]+)?' \
.venv-mlx/bin/uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

cd "${ROOT}/frontend"
BACKEND_INTERNAL_URL="${BACKEND_URL}" \
NEXT_PUBLIC_API_BASE_URL="${BACKEND_URL}" \
npm run dev -- --hostname 0.0.0.0 --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

trap 'kill ${BACKEND_PID} ${FRONTEND_PID} 2>/dev/null || true' INT TERM EXIT

echo "Backend:  ${BACKEND_URL}"
echo "Frontend: http://localhost:${FRONTEND_PORT}"
wait
