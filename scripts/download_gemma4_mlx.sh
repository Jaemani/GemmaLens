#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${1:-mlx-community/gemma-4-e4b-it-OptiQ-4bit}"
TARGET_DIR="${2:-$HOME/Models/mlx/gemma-4-e4b-it-OptiQ-4bit}"

mkdir -p "$TARGET_DIR"
hf download "$MODEL_ID" --local-dir "$TARGET_DIR"
