# Drown Platform

A self-hosted Platform-as-a-Service (PaaS) that lets you deploy applications with a simple `git push` — inspired by Heroku, built from scratch on a single cloud VM.

Push your code, get a live app with HTTPS in under a minute. Scale it with one command. Manage everything from a CLI or web dashboard.

---

## How It Works

```
git push platform main
        ↓
  Git hook triggers
        ↓
  Buildpacks detect your language & build a container image
        ↓
  Container starts, health check confirms it's responding
        ↓
  Caddy configures HTTPS + routing automatically
        ↓
  Your app is live at https://your-app.yourdomain.com
```

No Dockerfiles to write, no manual server config, no certificate management.

---

## Quick Start

**1. Install the CLI**
```bash
pip install drown
```

**2. Log in**

This authenticates you, generates an SSH key if you don't have one, registers it with the platform, and configures your local SSH — so `git push` just works afterward, with zero manual key setup.

```bash
drown login
```

**3. Create and deploy an app**
```bash
cd my-project/
git init
drown create my-app
git add .
git commit -m "Initial commit"
git push platform main
```

Your app is now live at `https://my-app.yourdomain.com`.

---

## CLI Reference

```bash
drown login                 # Authenticate and set up SSH access
drown apps                  # List your apps
drown create <app-name>     # Create a new app (or link to an existing one)
drown scale <app> <count>   # Scale to N replicas, load-balanced automatically
drown logs <app>            # View recent logs
drown metrics <app>         # CPU/memory usage per replica
```

---

## Scaling

```bash
drown scale my-app 3
```

Spins up additional containers and updates the reverse proxy to load-balance traffic across all of them — no downtime, no manual config. Scale back down the same way.

---

## Environment Variables

```bash
myplatform config:set my-app DATABASE_URL=postgres://...
```

Config is injected into the container on the next deploy. Redeploy to apply changes.

---

## Custom Domains

Add a `mini-heroku.json` file to your project root:

```json
{
  "domain": "myapp.example.com"
}
```

Push, and the platform automatically configures routing and issues a TLS certificate for it. No config file — you get a sensible default subdomain automatically.

---

## Multiple Users, Isolated Access

Each user gets their own account, owns their own apps, and pushes code with their own SSH key — restricted at the SSH layer itself so one user's key can never push to another user's app, even if they somehow knew the repository path.

An admin role exists for platform-wide visibility and management across all users' apps.

---

## Web Dashboard

Everything the CLI does, visually:
- App list with live status and replica counts
- Per-app view: logs, metrics, replicas, deployment history, config
- Guided onboarding when creating a new app
- Admin panel for managing all apps/users
- Dark mode (with light mode toggle)

---

## Architecture

```
control-plane/
├── main.py           # Triggered by every git push
└── core/
    ├── database.py      # Persistence (apps, replicas, users, config, history)
    ├── docker_ops.py      # Build, run, health-check, and monitor containers
    ├── caddy.py             # Regenerates routing/HTTPS config from current state
    ├── scaler.py               # Handles scaling and redeployment
    └── deploy.py                  # Orchestrates the full deploy pipeline

web/          # Flask dashboard + REST API
drown-cli/    # The `drown` CLI, published on PyPI
```

One shared engine (`core/`) powers every interface — git push, CLI, dashboard, and API — so behavior is always consistent no matter how you interact with the platform.

---

## Known Limitations

- **One deployable unit per repo.** Frontend/backend projects should be split into separate repos.
- **Frontend frameworks need a small config tweak.** Static site builders (React, Vite) can't be auto-detected as servable — add a `serve` script and `heroku-postbuild` step (the same requirement real Heroku has). Next.js works with zero config beyond specifying the port.
- **Manual scaling only, by design.** On a single-core host, auto-scaling wouldn't add real capacity — it would just create resource contention. Scaling is a deliberate, explicit action instead.
- **Single-node.** No multi-server clustering.

---

## Tech Stack

Docker · Cloud Native Buildpacks · Caddy · SQLite · Flask · Python · Click
