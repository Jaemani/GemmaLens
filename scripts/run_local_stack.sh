#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8012}"
FRONTEND_PORT="${FRONTEND_PORT:-3003}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
BACKEND_PYTHON="${BACKEND_PYTHON:-${ROOT}/backend/.venv/bin/python}"
DATABASE_URL="sqlite:///${ROOT}/tmp/dev-model-${BACKEND_PORT}.db"

mkdir -p "${ROOT}/tmp"

[[ -x "$BACKEND_PYTHON" ]] || { echo "Create backend/.venv or set BACKEND_PYTHON." >&2; exit 1; }
command -v node >/dev/null
"$BACKEND_PYTHON" - "$BACKEND_PORT" "$FRONTEND_PORT" <<'PY'
import socket
import sys

ports = [int(port) for port in sys.argv[1:]]
if len(set(ports)) != len(ports):
    raise SystemExit("Backend and frontend ports must differ.")
for port in ports:
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as error:
            raise SystemExit(f"Port {port} is unavailable; choose another port. Existing processes were not stopped.") from error
PY

RUNTIME_DIR="$(mktemp -d "${TMPDIR:-/tmp}/gemmalens-dev.XXXXXX")"
RUNTIME_CONFIG="${RUNTIME_DIR}/model_runtime.json"

cd "${ROOT}/backend"
APP_DEMO_MODE=true \
MODEL_PROVIDER=mock \
MODEL_SWITCHING_ENABLED=false \
MODEL_RUNTIME_CONFIG_PATH="${RUNTIME_CONFIG}" \
DATABASE_URL="${DATABASE_URL}" \
UPLOAD_STORAGE_DIR="${ROOT}/tmp/dev-uploads-${BACKEND_PORT}" \
TRANSCRIPT_CACHE_DIR="${ROOT}/tmp/dev-transcripts-${BACKEND_PORT}" \
LOCAL_MEDIA_LIBRARY_ENABLED=false \
CORS_ORIGINS="http://127.0.0.1:${FRONTEND_PORT}" \
"$BACKEND_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

cd "${ROOT}/frontend"
BACKEND_INTERNAL_URL="${BACKEND_URL}" \
NEXT_PUBLIC_API_BASE_URL="" \
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

cleanup() {
  trap - INT TERM EXIT
  kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  wait "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  rm -rf "${RUNTIME_DIR}"
}
trap cleanup INT TERM EXIT

echo "Mock backend (no model inference): ${BACKEND_URL}"
echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}"
wait
