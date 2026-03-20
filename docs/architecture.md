# OpenGitClaw Architecture Overview

OpenGitClaw is designed as a production-grade, enterprise-ready autonomous GitHub DevOps agent.

## High-Level Flow

1. GitHub events (PRs, issues, pushes) → secure webhook
2. Webhook verifies signature + IP → publishes to Redis stream
3. Redis event bus (persistent, HA-ready) → worker pool consumes
4. Worker → Planner: LLM generates validated multi-step task DAG
5. Planner executes graph:
   - Queries repo graph (Tree-sitter) & memory (LanceDB)
   - Delegates to modular skills
   - Runs risky actions in isolated Docker sandbox
6. Skills perform actions → GitHub API updates (PRs, comments, merges, releases)
7. Observability (Prometheus metrics + OpenTelemetry traces) captures everything
8. Background loop handles daily maintenance, cleanup, KPI reporting

## Key Components

- **Webhook Handler** — HMAC signature, GitHub IP allowlist, rate limiting, idempotency
- **Redis Event Bus** — persistent streams, dead-letter queue for failures
- **Planner Engine** — LLM + Pydantic validation, retries, SLA prioritization, DAG execution
- **Repo Graph & Indexer** — Tree-sitter AST parsing, function/call dependency graph, incremental indexing, node embeddings in LanceDB
- **Skills System** — versioned, modular (SOUL.md + Python), function-aware execution
- **Safe Sandbox** — Docker containers with resource limits, seccomp, auto-destroy
- **Observability** — Prometheus /metrics endpoint, OpenTelemetry tracing, KPI dashboard with predictive trends
- **Security & Compliance** — RBAC middleware, Vault secrets placeholder, audit logging stubs
- **Self-Healing** — daily TTL cleanup, retry/backoff, checkpointing

## Why This Design Wins

- Persistent & crash-resistant (Redis + idempotency)
- Scalable horizontally (stateless workers, Redis cluster-ready)
- Safe at enterprise scale (sandbox + graph-aware rollbacks)
- Intelligent (predictive ML + full repo understanding)
- Observable (metrics, traces, KPIs)
- Extensible (versioned skills marketplace)

This is not a simple bot — it's a full autonomous DevOps platform.
