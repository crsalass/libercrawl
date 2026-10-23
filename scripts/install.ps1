#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host 'Libercrawl setup — uses the upstream engine source code, never the hosted scraping API.' -ForegroundColor Cyan
foreach ($program in @('git','docker','python')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) { throw "$program is required. Install it first and reopen PowerShell." }
}
docker compose version | Out-Host
if (-not (Test-Path 'engine/.git')) {
    git clone --branch v2.11.0 --depth 1 https://github.com/firecrawl/firecrawl.git engine
    if ($LASTEXITCODE -ne 0) { throw 'Unable to clone the local extraction engine.' }
}
$headCommit = (git -C engine rev-parse HEAD).Trim()
$tagCommit = 'ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5'
if ($LASTEXITCODE -ne 0 -or $headCommit -ne $tagCommit) { throw "Unexpected upstream checkout: '$headCommit'. Expected pinned v2.11.0." }
# Apply the shared RabbitMQ fix. Fail if the pinned upstream Compose layout changes.
& python scripts/patch_engine.py engine/docker-compose.yaml
if ($LASTEXITCODE -ne 0) { throw 'RabbitMQ compatibility patch failed; inspect the pinned upstream Compose file.' }
if (Test-Path 'engine/.env') {
    (Get-Content 'engine/.env') -replace '^NUQ_BACKEND=postgres$', 'NUQ_BACKEND=pg' | Set-Content 'engine/.env'
}
if (-not (Test-Path 'engine/.env')) {
    $secretBytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($secretBytes) } finally { $rng.Dispose() }
    $secret = [BitConverter]::ToString($secretBytes).Replace('-','').ToLowerInvariant()
    @"
# Self-hosted engine only; loopback API port. No hosted services or paid model providers.
PORT=127.0.0.1:3002
USE_DB_AUTHENTICATION=false
BULL_AUTH_KEY=$secret
NUQ_BACKEND=pg
NUQ_WORKER_COUNT=1
NUM_WORKERS_PER_QUEUE=1
CRAWL_CONCURRENT_REQUESTS=2
MAX_CONCURRENT_JOBS=2
BROWSER_POOL_SIZE=1
OPENAI_API_KEY=
OPENAI_BASE_URL=
OLLAMA_BASE_URL=
POSTHOG_API_KEY=
PROXY_SERVER=
"@ | Set-Content 'engine/.env' -Encoding Ascii
}
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
if (-not (Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies installation failed.' }
Write-Host "`nInstalled. Run .\scripts\start.ps1 to build/start upstream engine and launch Libercrawl." -ForegroundColor Green
Write-Host 'First engine build downloads free open-source images/dependencies; no hosted scraping credits are used.'
