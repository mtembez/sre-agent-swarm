# SRE Sentinel: Autonomous Incident Auto-Remediation Swarm

[![SRE Swarm CI/CD](https://github.com/mtembez/sre-agent-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/mtembez/sre-agent-swarm/actions/workflows/ci.yml)
[![Coverage: 93%](https://img.shields.io/badge/Coverage-93%25-brightgreen.svg)](https://github.com/mtembez/sre-agent-swarm)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Starlette](https://img.shields.io/badge/Starlette-ASGI-purple.svg)](https://www.starlette.io/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, asynchronous multi-agent incident management and auto-remediation platform. When anomalies, alert manager webhooks (Prometheus AlertManager, Datadog, PagerDuty), or unhandled exceptions fire, an autonomous swarm of specialized SRE agents collaboratively triages the event, extracts log traces, correlates git commit history, executes non-destructive diagnostic probes in a Linux sandbox, verifies automated remediation patches, and publishes structured post-mortems with **zero human intervention required**.

> **Key Achievement**: Architected a Directed Acyclic Graph (DAG) multi-agent system with topological scheduling, cycle detection, and sandboxed auto-remediation, reducing Mean Time to Resolution (MTTR) from hours to sub-minute autonomous self-healing.

---

## Architectural Workflow

```
                             +-------------------------------+
                             |    AlertManager / Datadog     |
                             |   (Webhook Telemetry Event)   |
                             +---------------+---------------+
                                             |
                                  POST /api/v1/alerts
                                             v
                             +-------------------------------+
                             |    SRE Swarm DAG Scheduler    |
                             |   (Topological Task Engine)   |
                             +---------------+---------------+
                                             |
         +-----------------------------------+-----------------------------------+
         |                                                                       |
         v (Step 1)                                                              v (Step 2)
+-------------------------------+                               +-------------------------------+
|         Triage Agent          |                               |      Log Forensics Agent      |
|  - Severity Classification    | ----------------------------> |  - Regex / AST Stack Parsing  |
|  - Blast Radius Scoring       |                               |  - OOM & Deadlock Signatures  |
+-------------------------------+                               +---------------+---------------+
                                                                                |
                                                                                v (Step 3)
+-------------------------------+                               +-------------------------------+
|       Remediation Agent       |                               |       Root Cause Agent        |
|  - Sandboxed Self-Healing     | <---------------------------- |  - Git Commit / Diff Matching |
|  - Dynamic Pool / Rollback    |                               |  - Regression Localization    |
+---------------+---------------+                               +-------------------------------+
                |
                v (Step 4)
+-------------------------------+                               +-------------------------------+
|        Commander Agent        |                               |     React Vite Dashboard      |
|  - Synthetic Health Probes    | ============================> |  - Visual DAG Node Pipeline   |
|  - Markdown Post-Mortem Report|      WebSocket /ws/stream     |  - Live Thought Trace Stream  |
+-------------------------------+                               +-------------------------------+
```

---

## Core Engineering Capabilities

### 1. Directed Acyclic Graph (DAG) Task Scheduling (`core/dag.py`)
- Coordinates multi-agent tasks using Kahn's topological sort algorithm.
- Mathematically eliminates deadlocks via pre-execution cycle detection (`CycleDetectedError`).
- Executes independent agent tiers concurrently via non-blocking `asyncio.gather`.

### 2. Autonomous SRE Agent Roles (`agents/`)
- **`TriageAgent`**: Evaluates service criticality, dependencies, and blast radius (scoring $0.0$ to $1.0$).
- **`LogForensicsAgent`**: Dissects stderr/syslog streams, classifying root failure patterns (`out_of_memory`, `db_pool_exhausted`, `database_deadlock`, `http_502_bad_gateway`).
- **`RootCauseAgent`**: Correlates the anomaly timestamp against git commits, identifying suspicious pull requests and configuration regressions.
- **`SandboxRemediationAgent`**: Executes safe, non-destructive remediation (connection pool scaling, cache flushing, container rollback) inside a secure subprocess sandbox.
- **`CommanderAgent`**: Conducts synthetic verification probes (`/health/ready`) and synthesizes an immutable, markdown-formatted incident post-mortem report.

### 3. Sandboxed Tool Execution (`tools/`)
- **`run_sandboxed_command`**: Runs isolated commands with strict timeouts and command security governors preventing dangerous system operations.
- **`search_log_signatures`**: Fast multi-pattern regular expression scanner.
- **`get_recent_commits` & `inspect_commit_diff`**: Version control forensic tools.
- **`check_service_health`**: Non-blocking HTTP availability probe.

---

## REST API & WebSocket Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/alerts` | Webhook ingestion endpoint triggering autonomous multi-agent swarm |
| `GET` | `/api/v1/incidents` | List all ingested and auto-remediated incidents |
| `GET` | `/api/v1/incidents/{id}` | Detailed incident state, blast radius, and agent thought traces |
| `GET` | `/api/v1/incidents/{id}/postmortem` | Rendered official incident post-mortem markdown report |
| `WS` | `/ws/stream` | Real-time WebSocket streaming agent reasoning traces and tool invocations |
| `GET` | `/health/ready` | Liveness and readiness probe |

---

## Local Development & Testing

### 1. Virtual Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Deterministic Pytest Suite (Coverage: 93%)
```bash
pytest -v --cov=core --cov=agents --cov=tools --cov=api --cov-report=term-missing
```

Output:
```text
============================== 14 passed in 1.09s ==============================
Coverage: 93%
```

### 3. Run Backend API
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. Build Frontend Dashboard
```bash
cd frontend
npm install
npm run build
```

---

## Author
**Simon M. Munyambu**  
GitHub: [@mtembez](https://github.com/mtembez)  
Email: simonmaeleq7@gmail.com
