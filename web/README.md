# Drown Platform - Web Dashboard

A web UI for the Drown Platform (mini-Heroku PaaS) that visualizes deployed apps as drowning in an ocean.

## Features

- **Ocean Homepage**: Apps are displayed as bubbles that sink deeper based on their age
  - Non-linear depth calculation: newer apps sink fast, older apps approach the ocean floor asymptotically
  - Animated Docker whale swimming across the scene
  - Real-time stats: total apps, replicas, and oldest app age
  - Auto-refreshing stats every 30 seconds

- **App Detail Page**: Comprehensive view of each application
  - Domain, builder, and status information
  - Replica list with CPU/memory metrics
  - Environment variables (click to reveal values)
  - Recent logs from containers
  - Deployment history

## Installation

The dashboard is a standalone Flask app that imports from the existing control-plane modules.

### Prerequisites

- Python 3.8+
- Flask

### Setup

1. Install Flask if not already installed:
```bash
pip install flask
```

2. Run the dashboard:
```bash
cd /home/ubuntu/mini-heroku/web
python app.py
```

The dashboard will start on `http://0.0.0.0:5000`

## Architecture

- **Backend Integration**: Imports and reuses functions from `/home/ubuntu/mini-heroku/control-plane/core/`
  - `database.py` for all data queries
  - `docker_ops.py` for container metrics and logs
  - No modification to existing backend code

- **Frontend**: Server-rendered HTML with Jinja2 templates
  - No build step required
  - Lightweight CSS animations for ocean effects
  - Minimal JavaScript for auto-refresh and interactions

## API Endpoints

- `GET /` - Ocean homepage
- `GET /app/<app_name>` - App detail page
- `GET /api/stats` - JSON stats for auto-refresh
- `GET /api/app/<app_name>/metrics` - JSON metrics for auto-refresh

## Theme

Apps "drown" in an ocean over time:
- Surface (0-60px): Just deployed apps
- Mid-ocean (60-400px): Recent apps (days to weeks old)
- Deep ocean (400-700px): Older apps (weeks to months old)
- Ocean floor (700px+): Ancient apps

The depth formula: `depth = min(700, sqrt(days_old) * 50)`

This creates a realistic sinking effect where apps quickly descend from the surface but slow down as they approach the depths.
