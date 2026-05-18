#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export LLAMA_SERVER="${LLAMA_SERVER:-/opt/homebrew/bin/llama-server}"
export GEMMA4_26B_GGUF="${GEMMA4_26B_GGUF:-${HOME}/Models/gemma4-25.8B/gemma4-25.8B-Q4_K_M.gguf}"
export GEMMA4_31B_GGUF="${GEMMA4_31B_GGUF:-${HOME}/Models/gemma4-31.3b/gemma4-31.3B-Q4_K_M.gguf}"
export GEMMA4_GGUF_DEFAULT_MODEL="${GEMMA4_GGUF_DEFAULT_MODEL:-gemma4-26b-gguf}"
export LLAMA_CTX_SIZE="${LLAMA_CTX_SIZE:-4096}"
export LLAMA_THREADS="${LLAMA_THREADS:-8}"
export LLAMA_BATCH="${LLAMA_BATCH:-256}"
export LLAMA_UBATCH="${LLAMA_UBATCH:-128}"

cd "${ROOT}"
python3 scripts/thinkpad_gemma4_q4_server.py --host 0.0.0.0 --port 11445 --model "${GEMMA4_GGUF_DEFAULT_MODEL}"
