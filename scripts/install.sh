#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for executable in git docker python3; do command -v "$executable" >/dev/null || { echo "Missing $executable" >&2; exit 1; }; done
docker compose version
if [ ! -d engine/.git ]; then git clone --branch v2.11.0 --depth 1 https://github.com/firecrawl/firecrawl.git engine; fi
[ "$(git -C engine rev-parse HEAD)" = "ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5" ] || { echo 'Incorrect upstream version' >&2; exit 1; }
# Fix RabbitMQ healthcheck user race observed on the self-hosted stack.
bash scripts/patch-engine.sh
if [ -f engine/.env ]; then
  sed -i 's/^NUQ_BACKEND=postgres$/NUQ_BACKEND=pg/' engine/.env
fi
if [ ! -f engine/.env ]; then
  umask 077
  secret="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  cat > engine/.env <<CONFIG
PORT=127.0.0.1:3002
USE_DB_AUTHENTICATION=false
BULL_AUTH_KEY=${secret}
NUQ_BACKEND=pg
NUQ_WORKER_COUNT=1
NUM_WORKERS_PER_QUEUE=1
CRAWL_CONCURRENT_REQUESTS=2
MAX_CONCURRENT_JOBS=2
BROWSER_POOL_SIZE=1
OPENAI_API_KEY=
OPENAI_BASE_URL=
OLLAMA_BASE_URL=
PROXY_SERVER=
CONFIG
fi
[ -f .env ] || cp .env.example .env
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
printf '\nInstalled. Run ./scripts/start.sh\n'
