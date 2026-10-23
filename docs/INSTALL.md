# Install Libercrawl

> This guide covers the **public GitHub edition** of [Libercrawl](https://github.com/crsalass/libercrawl). It installs a **pinned, separately licensed Firecrawl extraction engine**; this is not a hosted scraping service. The original source and licensing details are preserved in [third-party notices](../THIRD_PARTY_NOTICES.md). Installation needs internet for Git, Python packages, container images, and browser dependencies; no hosted scraping account or API key is required.

## Before you start

**Planning estimate:** x86-64, 4+ CPU cores, 16 GB or more RAM available to the workload, and 50 GB or more free disk space, allowing additional resources for the host OS. A machine with 8 GB RAM and 30 GB free disk may work with reduced concurrency but is not guaranteed; smaller machines may fail during browser/container builds. No GPU is needed. These are not benchmarked minimums; ARM compatibility is unverified.

**Tools:** Git, Python 3 with `venv` and pip, Docker Engine, Docker Compose v2, outbound internet, and a modern browser. For Windows, use WSL2 running Ubuntu with systemd support; the required Linux tools run **inside Ubuntu**, not in PowerShell.

### Choose your platform

- **Linux / Ubuntu:** Follow [Install on Ubuntu](#install-on-ubuntu).
- **Windows 10/11:** Follow [Install with Windows + WSL2](#install-with-windows--wsl2), then run the Ubuntu steps.
- **macOS:** Docker Compose support is possible, but the current package has not been field-tested on macOS. Treat it as experimental and review its Docker/virtualization dependency licenses separately.

## Install with Windows + WSL2

1. Enable virtualization in your computer's firmware if it is disabled.
2. In **Windows PowerShell as Administrator**, install WSL if needed:

   ```powershell
   wsl --install -d Ubuntu
   ```

   Restart Windows if prompted. WSL2 supports Windows 10 (appropriate supported builds) and Windows 11. For compatibility instructions, see [Microsoft's official WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install).

3. In **Windows PowerShell**, verify Ubuntu is using version 2:

   ```powershell
   wsl -l -v
   ```

   If Ubuntu is version 1, run `wsl --set-version Ubuntu 2` before continuing.

4. Start Ubuntu from PowerShell:

   ```powershell
   wsl -d Ubuntu
   ```

   `wsl` commands run in **PowerShell**; `sudo`, `apt`, `systemctl`, `docker`, and `bash` run **inside Ubuntu**.

5. Confirm systemd is available inside Ubuntu with `ps -p 1 -o comm=`. If it is not `systemd`, follow [WSL2 systemd troubleshooting](TROUBLESHOOTING.md#docker-daemon-is-not-running-under-wsl2) before starting Docker. Then follow the Linux installation steps below. This path uses Docker Engine inside Ubuntu; Docker Desktop is not required.

**Security note for Windows 10:** Windows 10 version 22H2 reached end of standard security support in October 2025. Use Windows 11 or an applicable Extended Security Updates (ESU) arrangement for an internet-connected scraping machine. See [Microsoft’s lifecycle guidance](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support).

**Storage tip:** Place your project under `~/libercrawl`, not `/mnt/c/...`, for faster file access. By default, Ubuntu's virtual disk may live on C:. Advanced users can move the **entire WSL distribution** using `wsl --export` and `wsl --import` after stopping Docker, but migration is optional and should be backed up and verified before deleting anything.

## Install on Ubuntu

### 1. Install prerequisites

In Ubuntu:

```bash
sudo apt update
sudo apt install -y git curl docker.io docker-compose-v2 python3 python3-venv python3-pip
sudo systemctl enable --now docker
```

Verify:

```bash
docker --version
docker compose version
sudo docker run --rm hello-world
python3 --version
```

Ubuntu package names vary by distribution release. On an existing Docker installation, verify its version and Compose plugin first rather than mixing package sources. If `docker-compose-v2` is unavailable, follow Docker's [official installation instructions for Ubuntu](https://docs.docker.com/engine/install/ubuntu/) rather than guessing a replacement. If `python3 -m venv` reports missing `ensurepip`, install the matching version-specific package indicated by the terminal.

### 2. Docker permissions

The Docker socket is typically accessible only to `root` or members of the `docker` group. For a single trusted developer machine, you can use:

```bash
sudo usermod -aG docker "$USER"
```

On native Linux, log out and back in to refresh group membership. On WSL2, save work in all distributions, **exit Ubuntu**, and run these commands in Windows PowerShell (`wsl --shutdown` stops all running distributions):

```powershell
wsl --shutdown
wsl -d Ubuntu
```

Verify in your Linux terminal after signing back in or restarting Ubuntu:

```bash
groups
docker ps
```

`docker ps` should work without `sudo`. **Security warning:** `docker` group access is effectively root-equivalent. Do not add untrusted accounts.

### 3. Get Libercrawl

Clone the public repository inside your Linux home directory:

```bash
cd ~
git clone https://github.com/crsalass/libercrawl.git
cd libercrawl
```

Alternatively download the repository's Source ZIP, extract it into your Linux home folder, and enter the extracted folder. The public repository should **not** contain a downloaded `engine/`, a `.venv/`, local `.env` files, or database files.

### 4. Install Libercrawl and the extraction engine source

```bash
bash scripts/install.sh
```

The installer:

1. Confirms prerequisites and Docker Compose.
2. Clones the pinned engine release **`v2.11.0`**, verifies its pinned Git commit, and stores it in `engine/` (ignored by Git).
3. Applies an idempotent compatibility patch that runs RabbitMQ health checks under the correct `rabbitmq` user and allows a 120-second startup grace period for slower machines (`interval: 10s`, `timeout: 10s`, `retries: 10`). The startup scripts reapply this patch to existing installations after a code update.
4. Creates `engine/.env` configured for local use, including `NUQ_BACKEND=pg` (PostgreSQL).
5. Creates `.env`, sets up `.venv`, and installs dashboard Python packages.

It never contacts a hosted scraping API, but it does download open-source code and software dependencies from their distribution services.

Do **not** replace the pinned engine release with `main` without checking its Compose contract, settings, database schema, and patches.

### 5. Start the stack

```bash
bash scripts/start.sh
```

The script starts and builds the upstream Docker Compose services and launches the dashboard in your foreground terminal. You can follow output there; use another terminal for diagnostic commands. The first run may involve several gigabytes of downloads and a sizable Chromium/Playwright build.

Open:

- **Dashboard:** http://127.0.0.1:3210
- **Local extraction API:** http://127.0.0.1:3002

Neither endpoint should be exposed to the internet.

### 6. Check operation

In a second Ubuntu terminal:

```bash
docker ps
curl -s http://127.0.0.1:3210/api/status
```

Dashboard status should show `"engine": "online"`. This only confirms API responsiveness.

For a real end-to-end test, submit `https://example.org` through **Single scrape**, open **Archive → Inspect**, and confirm a completed job contains Markdown. Network restrictions at the target website can still prevent individual scrapes.

## Shut down and restart

To stop only the dashboard, press `Ctrl+C` in its running terminal. To stop the **Docker engine** too:

```bash
cd ~/libercrawl
bash scripts/stop.sh
```

Later start everything with:

```bash
cd ~/libercrawl
bash scripts/start.sh
```

The default Compose project name is `embercrawl-engine` for **backward compatibility** with earlier installs and Docker volume names. This is expected and is an internal container identifier, not product branding.

## Update policy and third-party licenses

Libercrawl pins a separately maintained engine version. For changes to upstream dependencies, update the pin only after reviewing release compatibility and running application tests and a real scrape. Back up `data/` and any engine state you need before upgrades. Avoid `docker compose down -v`, Docker volume deletion, and unreviewed `docker system prune` operations, which may destroy data.

Continue with [the User Guide](USER_GUIDE.md) or [Troubleshooting](TROUBLESHOOTING.md).
