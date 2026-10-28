# SRE Sentinel: Autonomous Incident Auto-Remediation Swarm

[![SRE Swarm CI/CD](https://github.com/mtembez/sre-agent-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/mtembez/sre-agent-swarm/actions/workflows/ci.yml)
[![Coverage: 95%](https://img.shields.io/badge/Coverage-95%25-brightgreen.svg)](https://github.com/mtembez/sre-agent-swarm)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Starlette](https://img.shields.io/badge/Starlette-ASGI-purple.svg)](https://www.starlette.io/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, asynchronous multi-agent incident management and auto-remediation platform. When anomalies, alert manager webhooks (Prometheus AlertManager, Datadog, PagerDuty), or unhandled exceptions fire, an autonomous swarm of specialized SRE agents collaboratively triages the event, extracts log traces, correlates git commit history, executes non-destructive diagnostic probes in a Linux sandbox, verifies automated remediation patches, and publishes structured post-mortems with **zero human intervention required**.

> **Key Achievement**: Architected a Directed Acyclic Graph (DAG) multi-agent system with topological scheduling, cycle detection, declarative SRE playbooks, and chaos engineering injection, reducing Mean Time to Resolution (MTTR) from hours to sub-minute autonomous self-healing.

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
|  - SRE Playbook Engine        | <---------------------------- |  - Git Commit / Diff Matching |
|  - Sandboxed Fix & Rollback   |                               |  - Regression Localization    |
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
- Eliminates deadlocks via pre-execution cycle detection (`CycleDetectedError`).
- Executes independent agent tiers concurrently via non-blocking `asyncio.gather`.

### 2. Declarative SRE Playbook Engine (`core/playbooks.py`)
- Version-controlled SRE playbooks mapping failure signatures to automated recovery actions:
  - **`PB-001`**: PostgreSQL Database Connection Pool Saturation Recovery (`db_pool_exhausted`).
  - **`PB-002`**: Container OOM Heap Saturation & Cache Eviction (`out_of_memory`, `oomkilled`).
  - **`PB-003`**: Upstream 502 Bad Gateway Auto-Rollback (`http_502_bad_gateway`, `connection_refused`).
  - **`PB-004`**: Log Volume Saturation & WAL Truncation (`no space left on device`).
- Pre-flight validation checks run inside the sandbox before executing any state changes.
- Automated rollback commands triggered immediately if any remediation step fails.

### 3. Chaos Engineering Fault Injection Lab (`chaos/`)
- Injects controlled production outages to evaluate autonomous recovery:
  - `db_pool_starvation`: Saturates active handles on primary pool (50/50).
  - `memory_leak`: Injects uncollected session growth exceeding 2GiB.
  - `cascading_503`: Simulates upstream dropped packets and HTTP 502/503 storms.
  - `disk_pressure`: Simulates `/var/log` volume exhaustion.
  - `network_latency`: Injects 1200ms cross-region latency breaching SLA bounds.
- Tracks drill resolution and computes exact Mean Time to Resolution (MTTR).

### 4. Telemetry & Anomaly Detection (`telemetry/`)
- Computes rolling latency percentiles ($P_{50}, P_{90}, P_{95}, P_{99}$) and error rate percentages.
- **Log Anomaly Detector**: Rolling $Z$-score statistical baseline ($Z > 2.5$) and Shannon entropy collapse monitoring.
- Exposes standard Prometheus text exposition format on `/metrics`.

### 5. SRE Sentinel CLI Interface (`cli.py`)
- Full command-line operational tooling:
  - `python cli.py trigger --service payment-gateway --error "PoolExhaustedError"`
  - `python cli.py chaos inject --type db_pool_starvation`
  - `python cli.py chaos list`
  - `python cli.py playbooks`
  - `python cli.py metrics`

---

## REST API & WebSocket Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/alerts` | Webhook ingestion endpoint triggering autonomous multi-agent swarm |
| `GET` | `/api/v1/incidents` | List all ingested and auto-remediated incidents |
| `GET` | `/api/v1/incidents/{id}` | Detailed incident state, blast radius, and agent thought traces |
| `GET` | `/api/v1/incidents/{id}/postmortem` | Rendered official incident post-mortem markdown report |
| `GET` | `/api/v1/playbooks` | List declarative SRE recovery playbooks |
| `POST` | `/api/v1/chaos/inject` | Trigger automated chaos fault injection drill |
| `GET` | `/api/v1/chaos/drills` | List active/past chaos drills with MTTR metrics |
| `GET` | `/metrics` | Prometheus metrics exposition format |
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

### 2. Run Deterministic Pytest Suite (Coverage: 95%)
```bash
pytest -v --cov=core --cov=agents --cov=tools --cov=api --cov=chaos --cov=telemetry --cov=cli --cov-report=term-missing
```

Output:
```text
============================== 32 passed in 3.32s ==============================
Coverage: 95%
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
