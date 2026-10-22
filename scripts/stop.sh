#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f engine/docker-compose.yaml ]; then docker compose --project-directory engine -p embercrawl-engine -f engine/docker-compose.yaml down; fi
echo 'Engine stopped. SQLite archive retained.'
