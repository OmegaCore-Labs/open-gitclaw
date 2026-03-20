# OpenGitClaw Deployment Guide

## Prerequisites

- Docker & docker-compose (or Kubernetes for production)
- GitHub App (use manifest.yml)
- Redis server (or Redis cluster for HA)
- Prometheus (optional, for metrics)
- uv or pip for local dev

## Quick Local Start

1. Clone repo
   git clone https://github.com/yourusername/open-gitclaw.git
   cd open-gitclaw

2. Copy env
   cp .env.example .env
   # Edit .env with your GitHub App credentials, webhook secret, etc.

3. Start stack
   docker compose up --build

4. Create & install GitHub App
   - Go to https://github.com/settings/apps/new
   - Upload manifest.yml
   - Set webhook URL to http://localhost:8000/webhook (or your public URL)
   - Install on your test repos

5. Verify
   - Open http://localhost:8000/dashboard
   - Make a test PR → watch logs

## Production Deployment (Kubernetes / Cloud)

1. Use HA Redis (Redis Sentinel or Cluster)
2. Deploy with Kubernetes (sample manifests coming soon)
   - Stateless worker pods
   - Redis statefulset
   - Prometheus operator
3. Secure webhook endpoint
   - Use HTTPS + domain
   - Cloudflare/NGINX proxy
   - Vault for secrets
4. Scale
   - Horizontal pod autoscaling on queue length
   - Multi-region with Redis replication
5. Monitoring
   - Prometheus scrape /metrics:8001
   - Grafana dashboards for KPIs
   - Alerts on failed plans, high latency, queue backlog

## Monitoring Endpoints

- Health: GET / → {"status": "alive"}
- Dashboard: GET /dashboard → KPIs + trends
- Metrics: GET /metrics → Prometheus format

## Upgrading

- git pull
- docker compose down
- docker compose up --build

Questions? Open an issue.
