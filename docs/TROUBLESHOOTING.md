# Troubleshooting

This document captures real issues encountered in a Windows 10 + WSL2 deployment. Run **PowerShell commands in Windows** and **Bash commands inside Ubuntu**.

## Dashboard displays Offline

1. Inspect Docker services:

   ```bash
   docker ps -a
   ```

2. Check if the local extraction API is answering:

   ```bash
   curl -i --max-time 10 http://127.0.0.1:3002/v2/scrape
   ```

   A GET may yield 404/405; this is not a real scrape test. Prefer the invalid-JSON route probe below:

   ```bash
   curl -i --max-time 10 -X POST http://127.0.0.1:3002/v2/scrape \
      -H 'Content-Type: application/json' -d '{}'
   ```

   **400 or 422** usually means the route exists and rejects missing URL data. **Connection refused** usually means the API is stopped/not bound. The `/test` endpoint is **not available in the pinned engine**; 404 there does not mean the engine is down.

3. Inspect API logs:

   ```bash
   docker logs --tail 100 embercrawl-engine-api-1
   ```

4. If the API is up, check the dashboard:

   ```bash
   curl -s http://127.0.0.1:3210/api/status
   ```

   If dashboard code or `.env` changed, restart the Uvicorn process. Changing frontend source may also require a hard refresh in the browser.

## API exits with `ZodError` / `NUQ_BACKEND`

The pinned engine expects the exact values `pg` or `fdb`; **`postgres` is not valid**. Use PostgreSQL unless intentionally operating FoundationDB:

```bash
grep '^NUQ_BACKEND=' engine/.env
# Expected: NUQ_BACKEND=pg
```

To correct a legacy misconfiguration, make a backup and edit `engine/.env`:

```bash
cp -p engine/.env engine/.env.backup
sed -i 's/^NUQ_BACKEND=postgres$/NUQ_BACKEND=pg/' engine/.env
```

Then recreate **only the API container** (from the repo root):

```bash
docker compose --project-directory engine -p embercrawl-engine \
  -f engine/docker-compose.yaml up -d --no-deps --force-recreate api
```

If this does not apply cleanly, inspect your exact pinned Compose file rather than deleting volumes.

## RabbitMQ unhealthy / `.erlang.cookie: eacces`

Inspect logs:

```bash
docker logs --tail 100 embercrawl-engine-rabbitmq-1
```

On an affected setup RabbitMQ exited because its cookie file was not readable by the RabbitMQ user. `scripts/install.sh` invokes `scripts/patch-engine.sh` to change the Compose health check to run under `rabbitmq` rather than `root`. If the patch is absent, from the repository root:

```bash
bash scripts/patch-engine.sh
docker compose --project-directory engine -p embercrawl-engine \
  -f engine/docker-compose.yaml up -d --no-deps --force-recreate rabbitmq
```

Then verify:

```bash
docker ps --filter 'name=embercrawl-engine-rabbitmq'
docker exec -u rabbitmq embercrawl-engine-rabbitmq-1 rabbitmq-diagnostics -q check_running
```

### RabbitMQ starts, but Compose reports it as unhealthy

On slower machines, the pinned upstream Compose file's **5-second** startup grace period can expire before RabbitMQ finishes booting. The logs can show `not running or has not fully booted yet` followed by a successful diagnostic (`ExitCode 0`). This is a startup race, not necessarily a cookie permissions error.

The public compatibility patch now also sets RabbitMQ's health check to:

```yaml
    healthcheck:
      test: ["CMD", "gosu", "rabbitmq", "rabbitmq-diagnostics", "-q", "check_running"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 120s
```

`start_period` is a **grace period for failed checks**, not a mandatory two-minute delay. The patch runs during both installation and normal startup. To apply it manually without reinstalling or deleting volumes:

```bash
bash scripts/patch-engine.sh
docker compose --project-directory engine -p embercrawl-engine \
  -f engine/docker-compose.yaml config --quiet
docker compose --project-directory engine -p embercrawl-engine \
  -f engine/docker-compose.yaml up -d --no-deps rabbitmq
```

Then examine the running health status and recent probes:

```bash
docker inspect --format '{{.State.Health.Status}}' embercrawl-engine-rabbitmq-1
docker inspect --format '{{range .State.Health.Log}}{{println .ExitCode .Output}}{{end}}' embercrawl-engine-rabbitmq-1
```

The patch only modifies the ignored, locally downloaded `engine/docker-compose.yaml`; it does not alter your private files or Docker volumes. If the upstream Compose format is unexpected, the patch exits with an error rather than silently changing another service.

Do not delete RabbitMQ state or loosen its cookie permissions broadly without confirming the exact failure.

## FoundationDB init says `Database already exists`

If the API is working with `NUQ_BACKEND=pg`, a failed FoundationDB initialization container that says *Database already exists* may be the result of an initialization step running a second time. **Do not reset the database just to clear that message.** Check API readiness and queue/database logs first.

## Docker: permission denied for `/var/run/docker.sock`

The user is not allowed to access Docker. On a trusted developer machine:

```bash
sudo usermod -aG docker "$USER"
```

Log out/in or restart WSL from Windows PowerShell:

```powershell
wsl --shutdown
wsl -d Ubuntu
```

Then `docker ps` should work. Docker group membership is root-equivalent; use caution.

## Docker pulls fail: `lookup registry-1.docker.io` / DNS timeout

Test DNS and network connectivity inside Ubuntu:

```bash
getent ahostsv4 registry-1.docker.io
cat /etc/resolv.conf
resolvectl status
ip -4 route
```

Check Windows DNS in **PowerShell**:

```powershell
Resolve-DnsName registry-1.docker.io
```

If Windows works but WSL does not, investigate WSL's resolver integration, VPN/firewall rules, and the `systemd-resolved` service. On some Windows 10 configurations, WSL's resolver stub `127.0.0.53` has **no upstream DNS servers**. Configure a working DNS source and confirm its persistence across `wsl --shutdown` before retrying large downloads. DNS tunneling is Windows-version dependent; do not assume Windows 10 supports the Windows 11 setting. Changing `/etc/resolv.conf` should be a **diagnosed, reversible** step, not the first troubleshooting action.

## Python `venv` or `ensurepip` is missing

Example:

```text
The virtual environment was not created successfully because ensurepip is not available
```

Install the package matching your Ubuntu `python3` version, then recreate the incomplete virtual environment:

```bash
python3 --version
sudo apt update
sudo apt install -y python3-venv
# If the error asks for a specific version, e.g. python3.14-venv, install that exact package.
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip --version
```

The `.venv` directory holds only local Python dependencies; removing it does not delete saved scrape data or the engine checkout.

## Chromium/Playwright Docker build fails downloading `xvfb`

A Debian package mirror may time out during `npx playwright install chromium --with-deps`. Retry the build after checking DNS/network stability:

```bash
bash scripts/start.sh
```

Docker normally reuses successful cached layers. If this repeats, investigate the exact mirror/network error. Do not delete your Docker images/cache reflexively.

## Nothing appears after clicking Inspect

This was addressed in the public v1.1.3 frontend: Inspect should open/focus the details area or display a visible error. Refresh the page with `Ctrl+Shift+R`, verify the backend is reachable, and check the browser console for an error. To verify the job exists:

```bash
curl -s http://127.0.0.1:3210/api/jobs
```

If you've mixed an old frontend with a new backend, update both from the same release package.

## Windows terminal confusion

- `PS C:\...>` or `PS D:\...>` means **PowerShell**. Use `wsl -l -v`, `wsl -d Ubuntu`, or `wsl --shutdown` here.
- `username@host:~$` means **Ubuntu**. Use `sudo`, `apt`, `docker`, `bash scripts/start.sh` here.
- `echo "$WSL_DISTRO_NAME"` inside Ubuntu prints the *active distribution name*.
- `/mnt/d/...` is merely a Windows drive mount location inside Linux; it does not identify where the WSL virtual disk itself is stored.

## Do not use destructive commands as a first resort

Avoid running `docker system prune -a`, `docker compose down -v`, `wsl --unregister ...`, or deleting `.env`, `engine/`, `data/`, Docker volumes, or WSL virtual disks unless you know which data will be lost and have a tested backup.
