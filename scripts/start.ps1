#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path 'engine/docker-compose.yaml')) { throw 'Run .\scripts\install.ps1 first.' }
if (-not (Test-Path '.venv/Scripts/python.exe')) { throw 'Python environment missing. Run install.ps1.' }
# Apply to existing installations after a git pull as well as fresh installs.
& python scripts/patch_engine.py engine/docker-compose.yaml
if ($LASTEXITCODE -ne 0) { throw 'RabbitMQ compatibility patch failed; inspect the pinned upstream Compose file.' }
Write-Host 'Starting self-hosted extraction engine (no hosted scraping API used)...' -ForegroundColor Cyan
docker compose --project-directory engine -p embercrawl-engine -f engine/docker-compose.yaml up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Engine startup failed. Check Docker Desktop and engine logs.' }
Write-Host 'Dashboard: http://127.0.0.1:3210' -ForegroundColor Green
Write-Host 'local extraction API: http://127.0.0.1:3002'
Write-Host 'Press Ctrl+C to stop the dashboard. Run .\scripts\stop.ps1 to stop engine containers.'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3210
