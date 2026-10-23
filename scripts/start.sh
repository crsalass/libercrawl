#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f engine/docker-compose.yaml ] && [ -x .venv/bin/python ] || { echo 'Run ./scripts/install.sh first' >&2; exit 1; }
# Apply to existing installations after a git pull as well as fresh installs.
bash scripts/patch-engine.sh
docker compose --project-directory engine -p embercrawl-engine -f engine/docker-compose.yaml up -d --build
echo 'Open http://127.0.0.1:3210 (local extraction API at http://127.0.0.1:3002)'
echo 'Ctrl+C stops dashboard; ./scripts/stop.sh stops engine.'
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 3210
