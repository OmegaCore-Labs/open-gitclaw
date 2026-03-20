# 🦞 OpenGitClaw — The Autonomous GitHub Agent That Actually Maintains Your Repos

Let AI review PRs, fix bugs, write tests, update docs, upgrade dependencies, triage issues and generate changelogs — **while you sleep**.

Built for developers and teams who are tired of manual repo chores.

## One-Command Start

```bash
git clone https://github.com/yourusername/open-gitclaw.git
cd open-gitclaw
uv sync          # or pip install -r requirements.txt
docker compose up --build
Then:

Create GitHub App from manifest.yml
Fill .env from .env.example
Install app on your repos
→ OpenGitClaw starts watching and working immediately

What It Does (Automatically)

Reviews every PR with full repo context and dependency graph
Generates & applies safe code fixes → opens fix PRs
Detects high-risk changes and prioritizes them (predictive ML scoring)
Adds missing tests in isolated Docker sandbox
Keeps README, docs, diagrams up-to-date
Safely upgrades dependencies and validates them
Triages, labels, replies to, or auto-closes issues
Writes beautiful changelogs and release notes

All coordinated by a smart planner that builds multi-step task graphs — no more one-off bots.
Simple Architecture Flow
GitHub Events ──► Webhook (secure) ──► Redis Bus (persistent) ──► Planner (LLM + graph)
│
┌──────────┼──────────┐
▼          ▼          ▼
Repo Graph    Skills      Observability
(Tree-sitter)   (modular)     (metrics + KPIs)
│
▼
Safe Sandbox (Docker)
│
▼
GitHub Updates (PRs, merges, comments)
Daily Self-Maintenance (Runs Automatically)

Refreshes security & indexes repos incrementally
Scans for outdated dependencies & docs drift
Cleans up stale issues & memory (TTL)
Reports KPIs & predicts repo health trends

Why OpenGitClaw Stands Out

Understands your whole codebase with function-level dependency graphs (not just diffs)
Predicts which PRs will break things before they merge
Auto-fixes and auto-rolls back safely — graph-aware
Enterprise-ready from day one: Prometheus metrics, tracing, HA Redis, Kubernetes notes
Self-healing: daily cleanup, retries, checkpointing, dead-letter queue
Modular skills you can extend without touching core code

Most AI GitHub bots stop at comments or simple suggestions.
OpenGitClaw actually ships code and maintains repos like a senior engineer on 24/7 duty.
Try It Now
Star this repo if you want more autonomous DevOps.
Fork → run → watch your repos improve themselves.
Questions or ideas? Open an issue — contributions welcome.
Made with 🦞 in 2026.
Enterprise observability: Real metrics, tracing, and KPI dashboards
Safe & compliant: Isolated sandbox, audit logs, RBAC-ready
Production-ready: HA bus, checkpointing, incremental indexing, Kubernetes support
