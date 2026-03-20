# 🦞 OpenGitClaw — #1 Enterprise AI DevOps Agent

Autonomous GitHub agent with enterprise-grade features: multi-step planning, dependency graph intelligence, persistent event bus, repository indexing, sandboxed execution, observability, and predictive insights.

## Core Features

- Graph-driven automation — function-level impact analysis and auto-rollbacks
- SLA-prioritized task planning — high-risk PRs and tasks handled first
- Predictive PR risk scoring — ML-based forecasting of failure probability
- Safe execution — Docker sandbox for tests and code changes
- Enterprise observability — Prometheus metrics, OpenTelemetry tracing, KPI dashboard
- Persistent & scalable — Redis event bus with dead-letter queue
- Self-healing — daily maintenance, incremental indexing, automatic retries

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/open-gitclaw.git
cd open-gitclaw

# Install dependencies (uv recommended)
uv sync

# Start (includes Redis & Prometheus)
docker compose up --build

Create a GitHub App using manifest.yml
Copy .env.example → .env and fill in values
Install the app on your repositories
The agent starts watching events automatically

Architecture Overview (Text Flow)
textGitHub Events (PR / Issue / Push)
          │
          ▼
Webhook Handler ──► Redis Event Bus (Persistent + DLQ)
                             │
                             ▼
                   Worker Pool (Async Processing)
                             │
                             ▼
                      Planner Engine
                (LLM + Validation + SLA Prioritization)
                 ├───────────────┬───────────────┐
                 ▼               ▼               ▼
         Repo Graph        Skills Execution    Observability
     (Tree-sitter +     (Versioned & Function-Aware)  (Prometheus + OTel)
      LanceDB Memory)           │                    KPI Dashboard
                 │               ▼
                 └──────► Safe Docker Sandbox
                                 │
                                 ▼
                          GitHub Actions
                    (Fix PRs / Merge / Comment / Rollback)
PR Processing Flow (Text)
textPR Opened / Updated
          │
          ▼
Webhook → Redis Bus → Worker
          │
          ▼
Planner creates task graph
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
Analyze  Generate  Run Tests
Diff     Patch      in Sandbox
   │      │           │
   └──────┼───────────┘
          ▼
   Update Docs / Dependencies
          │
          ▼
Open Fix PR or Auto-Merge
   (Graph-driven rollback if needed)
Daily Maintenance Flow (Text)
textBackground Loop (Hourly / Daily)
          │
          ▼
Refresh GitHub IPs + Security
          │
          ▼
Planner: Daily Task Graph
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
Incremental   Dependency   Stale Issue
Repo Indexing  & Docs       Triage
          │      Updates     │
          └──────┼───────────┘
                 ▼
          Memory Cleanup (TTL)
                 │
                 ▼
          KPI Report & Trends
Enterprise Feature Comparison







































































CategoryOpenGitClaw (#1 Enterprise)Typical Startup AI AgentKey DifferentiatorPlanner & DAGSLA-prioritized, predictive, graph-awareBasic sequencingHigh-risk PRs first, dependency resolutionAuto-Merge & RollbackGraph-driven, automatic rollbackManual or noneSafe, dependency-aware revertsRepo UnderstandingMulti-repo, node-level embeddingsSingle repo or shallowCross-repo impact analysisPredictive IntelligenceML-based PR risk & KPI forecastingNoneForecasts failure probability & trendsObservabilityPrometheus, OpenTelemetry, KPI dashboardBasic logsEnterprise metrics & tracingReliabilityCheckpointing, DLQ, HA Redis, K8s-readySingle instanceSelf-healing, crash-resistantSecurity & ComplianceRBAC, Vault, audit logsBasic authRegulatory-readyExtensibilityVersioned skills marketplaceStatic or single-versionDynamic, modular AI skillsSelf-Healing & MaintenanceContinuous, auto-indexing, daily checksManual triggersMinimal human interventionScalingKubernetes, multi-region supportLocal / single containerEnterprise-scale deployment
Why OpenGitClaw is #1

Predictive + self-healing: Forecasts risks and automatically recovers from failures
Graph intelligence: Understands function dependencies across repositories
Enterprise observability: Real metrics, tracing, and KPI dashboards
Safe & compliant: Isolated sandbox, audit logs, RBAC-ready
Production-ready: HA bus, checkpointing, incremental indexing, Kubernetes support
