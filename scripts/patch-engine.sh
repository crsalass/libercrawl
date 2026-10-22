#!/usr/bin/env bash
# Idempotent compatibility patch for the pinned upstream engine release.
# Only touches RabbitMQ's diagnostic healthcheck; never touches live volumes.
set -euo pipefail
cd "$(dirname "$0")/.."
compose=engine/docker-compose.yaml
[ -f "$compose" ] || { echo "Missing $compose" >&2; exit 1; }
python3 - "$compose" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); raw = p.read_text()
old = 'test: ["CMD", "rabbitmq-diagnostics", "-q", "check_running"]'
new = 'test: ["CMD", "gosu", "rabbitmq", "rabbitmq-diagnostics", "-q", "check_running"]'
if new in raw:
    print('RabbitMQ healthcheck already patched')
elif old in raw:
    p.write_text(raw.replace(old, new, 1))
    print('RabbitMQ healthcheck patched')
else:
    print('Unknown RabbitMQ healthcheck format: no changes made (review upstream Compose)')
PY
