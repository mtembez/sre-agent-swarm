# SRE Incident Auto-Remediation Swarm: Technical Specification

## Overview
An asynchronous multi-agent orchestration platform designed for autonomous Site Reliability Engineering (SRE). The system ingests telemetry alerts, isolates root causes across distributed application logs and git commits, executes non-destructive remediation experiments inside an isolated sandbox, verifies service recovery, and generates immutable post-mortem incident analyses.

## Core System Architecture
1. **DAG Workflow Engine (`core/engine.py`)**:
   - Directed Acyclic Graph orchestrating task dependencies.
   - Topological sorting using Kahn's algorithm with cycle detection.
   - Concurrent task execution using non-blocking Python `asyncio`.
2. **Autonomous ReAct State Machine (`core/agent.py`)**:
   - Discrete state transitions: `IDLE` -> `THINKING` -> `ACTION_CALL` -> `OBSERVATION` -> `RESOLVED` / `ESCALATED`.
   - Circuit breakers for max iterations and recursion traps.
3. **SRE Agent Roles (`agents/`)**:
   - `TriageAgent`: Ingests alerts, classifies severity, calculates blast radius.
   - `LogForensicsAgent`: Regex & semantic pattern recognition on application stderr/syslog.
   - `RootCauseAgent`: Correlates time of incident with recent commits and config changes.
   - `SandboxRemediationAgent`: Executes isolated patches, container rollbacks, or service restarts.
   - `CommanderAgent`: Synthesizes timeline and publishes markdown post-mortems.
4. **Tool Sandbox (`tools/`)**:
   - `SubprocessSandboxTool`: Isolated process execution with strict CPU time and memory bounds.
   - `LogSearchTool`: Fast indexed log parsing.
   - `GitDiffTool`: Version control inspection.
   - `HealthProbeTool`: Synthetic HTTP availability testing.
