#!/usr/bin/env bash
# Apply the same idempotent, fail-closed RabbitMQ compatibility fix on Linux.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/patch_engine.py engine/docker-compose.yaml
