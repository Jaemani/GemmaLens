#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Select Python 3.12 first"'
node -e 'if (Number(process.versions.node.split(".")[0]) !== 22) throw new Error("Select Node 22 first")'
"$PYTHON_BIN" -m venv "$ROOT/backend/.venv"
if [[ "$(uname -s)" == Linux ]]; then
  "$ROOT/backend/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements-linux.lock.txt"
else
  "$ROOT/backend/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements-dev.txt"
fi
cd "$ROOT/frontend"
npm ci
echo "Development dependencies installed. No services or model runtimes were started."
