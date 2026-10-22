#Requires -Version 5.1
$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path 'engine/docker-compose.yaml') {
    docker compose --project-directory engine -p embercrawl-engine -f engine/docker-compose.yaml down
}
Write-Host 'Engine containers stopped. Your SQLite archive is preserved in data/.'
