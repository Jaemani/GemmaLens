#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
MODEL_PROVIDER=mlx \
MLX_MODEL_PATH="${MLX_MODEL_PATH:-$HOME/Models/mlx/gemma-4-e4b-it-OptiQ-4bit}" \
.venv-mlx/bin/uvicorn app.main:app --reload --reload-exclude ".venv*" --host 127.0.0.1 --port 8000
