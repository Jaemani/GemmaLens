#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${1:-mlx-community/gemma-4-e4b-it-bf16}"
TARGET_DIR="${2:-$HOME/Models/mlx/gemma-4-e4b-it-bf16}"

mkdir -p "$TARGET_DIR"
hf download "$MODEL_ID" --local-dir "$TARGET_DIR"
