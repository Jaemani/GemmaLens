#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8012}"
RUNTIME_CONFIG="${ROOT}/tmp/funnel-model-runtime-${BACKEND_PORT}.json"
DATABASE_URL="${DATABASE_URL:-sqlite:///${ROOT}/tmp/funnel-model-${BACKEND_PORT}.db}"

if [[ -z "${BACKEND_API_KEY:-}" ]]; then
  echo "Set BACKEND_API_KEY before running this script." >&2
  echo "Example: BACKEND_API_KEY=\"$(openssl rand -hex 24)\" ./scripts/run_funnel_backend.sh" >&2
  exit 1
fi

mkdir -p "${ROOT}/tmp"

cd "${ROOT}/backend"
MODEL_PROVIDER="${MODEL_PROVIDER:-mlx}" \
MODEL_SWITCHING_ENABLED="${MODEL_SWITCHING_ENABLED:-true}" \
MODEL_RUNTIME_CONFIG_PATH="${RUNTIME_CONFIG}" \
DATABASE_URL="${DATABASE_URL}" \
LOCAL_MEDIA_LIBRARY_ENABLED="${LOCAL_MEDIA_LIBRARY_ENABLED:-false}" \
REMOTE_GEMMA_BASE_URL="${REMOTE_GEMMA_BASE_URL:-http://127.0.0.1:11444}" \
CORS_ALLOW_ORIGIN_REGEX="${CORS_ALLOW_ORIGIN_REGEX:-https?://(.*\\.vercel\\.app|localhost|127\\.0\\.0\\.1)(:[0-9]+)?}" \
BACKEND_API_KEY="${BACKEND_API_KEY}" \
.venv-mlx/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
