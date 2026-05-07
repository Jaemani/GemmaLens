#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
python3.12 -m venv .venv-mlx
.venv-mlx/bin/pip install -r requirements.txt
.venv-mlx/bin/pip install -r requirements-mlx.txt
