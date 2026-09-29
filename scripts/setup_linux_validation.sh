#!/usr/bin/env bash
# Prepare a fresh user service; do not start it or enable boot startup.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo "Linux is required." >&2; exit 1; }
[[ -x "$ROOT/backend/.venv/bin/python" ]] || { echo "Create backend/.venv first." >&2; exit 1; }
command -v openssl >/dev/null
command -v systemctl >/dev/null
for target in "$HOME/.local/share/gemmalens" "$HOME/.local/state/gemmalens" \
  "$HOME/.config/gemmalens" "$HOME/.config/systemd/user/gemmalens-api.service"; do
  if [[ -e "$target" || -L "$target" ]]; then
    echo "Refusing to overwrite existing path: $target" >&2
    exit 1
  fi
done

umask 077
mkdir -p "$HOME/.local/share/gemmalens" "$HOME/.local/state/gemmalens" \
  "$HOME/.config/gemmalens" "$HOME/.config/systemd/user"
ln -s "$ROOT" "$HOME/.local/share/gemmalens/current"
{
  printf 'BACKEND_API_KEY=%s\n' "$(openssl rand -hex 32)"
  printf 'CORS_ORIGINS=http://127.0.0.1:13003\n'
} > "$HOME/.config/gemmalens/api.env"
install -m 600 "$ROOT/deploy/systemd/gemmalens-api.service" \
  "$HOME/.config/systemd/user/gemmalens-api.service"
systemd-analyze --user verify "$HOME/.config/systemd/user/gemmalens-api.service"
systemctl --user daemon-reload
echo "Prepared gemmalens-api.service; inactive and not enabled."
