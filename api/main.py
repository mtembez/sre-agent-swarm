"""High-performance asynchronous Starlette ASGI server exposing incident ingestion and telemetry streams."""

import asyncio
import json
from typing import Any, Dict, List
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from chaos.injector import ChaosInjector, ChaosType
from core.events import EventBus
from core.models import Alert, AlertSeverity
from core.playbooks import PLAYBOOK_REGISTRY
from core.swarm import SRESwarmOrchestrator
from telemetry.metrics import MetricsTracker

orchestrator = SRESwarmOrchestrator()
chaos_injector = ChaosInjector(orchestrator)
event_bus = EventBus.get_instance()
metrics_tracker = MetricsTracker.get_instance()
connected_websockets: List[WebSocket] = []


async def health_live(request: Request):
    return JSONResponse({"status": "UP"})


async def health_ready(request: Request):
    return JSONResponse({"status": "READY", "version": "1.0.0"})


async def get_metrics(request: Request):
    """Prometheus metrics endpoint."""
    return PlainTextResponse(metrics_tracker.generate_prometheus_metrics(), media_type="text/plain; version=0.0.4")


async def list_playbooks(request: Request):
    """List declarative SRE recovery playbooks."""
    pbs = [
        {
            "playbook_id": pb.playbook_id,
            "name": pb.name,
            "match_signatures": pb.match_signatures,
            "steps_count": len(pb.remediation_steps),
            "post_verification_assertion": pb.post_verification_assertion,
        }
        for pb in PLAYBOOK_REGISTRY.values()
    ]
    return JSONResponse(pbs)


async def inject_chaos(request: Request):
    """Inject simulated production fault and monitor autonomous Swarm resolution."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    type_str = body.get("chaos_type", "db_pool_starvation")
    try:
        chaos_type = ChaosType(type_str)
    except ValueError:
        return JSONResponse({"error": f"Invalid chaos type. Supported: {[c.value for c in ChaosType]}"}, status_code=400)

    drill = await chaos_injector.inject_fault(chaos_type)
    return JSONResponse(drill.model_dump(mode="json"))


async def list_drills(request: Request):
    """List past and active chaos drills with MTTR metrics."""
    drills = [d.model_dump(mode="json") for d in chaos_injector.list_drills()]
    return JSONResponse(drills)


async def ingest_alert(request: Request):
    """Webhook ingestion endpoint to trigger multi-agent auto-remediation swarm."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    title = body.get("title", "Unhandled Incident")
    service = body.get("service", "unknown-service")
    severity_str = body.get("severity", "HIGH").upper()
    severity = AlertSeverity.__members__.get(severity_str, AlertSeverity.HIGH)
    error_message = body.get("error_message", "Service failure detected")

    raw_payload = {
        "logs": body.get("logs", ""),
        "deployed_commit": body.get("deployed_commit", "a1b2c3d"),
        "health_url": body.get("health_url", "http://localhost:8080/health/ready"),
    }

    alert = Alert(
        title=title,
        service=service,
        severity=severity,
        error_message=error_message,
        raw_payload=raw_payload,
    )

    state = await orchestrator.handle_alert(alert)

    return JSONResponse({
        "incident_id": state.incident_id,
        "status": state.status.value,
        "root_cause": state.root_cause,
        "remediation_action": state.remediation_action_taken,
        "remediation_success": state.remediation_success,
        "verification_passed": state.verification_passed,
    })


async def list_incidents(request: Request):
    """List all ingested and remediated incidents."""
    incidents = [
        {
            "incident_id": inc.incident_id,
            "title": inc.alert.title,
            "service": inc.alert.service,
            "severity": inc.alert.severity.value,
            "status": inc.status.value,
            "timestamp": inc.alert.timestamp.isoformat(),
            "remediation_success": inc.remediation_success,
        }
        for inc in orchestrator.active_incidents.values()
    ]
    return JSONResponse(incidents)


async def get_incident(request: Request):
    """Retrieve detailed state, DAG steps, thoughts, and timeline of an incident."""
    incident_id = request.path_params["incident_id"]
    inc = orchestrator.get_incident(incident_id)
    if not inc:
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    return JSONResponse(inc.model_dump(mode="json"))


async def get_postmortem(request: Request):
    """Retrieve markdown-formatted official post-mortem report."""
    incident_id = request.path_params["incident_id"]
    inc = orchestrator.get_incident(incident_id)
    if not inc:
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    if not inc.postmortem_markdown:
        return JSONResponse({"error": "Post-mortem not yet generated"}, status_code=400)
    return JSONResponse({"postmortem_markdown": inc.postmortem_markdown})


async def websocket_stream(websocket: WebSocket):
    """Real-time WebSocket endpoint streaming agent thoughts, tool calls, and state transitions."""
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        # Send recent events
        for evt in event_bus.get_history()[-20:]:
            await websocket.send_json(evt)

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


async def broadcast_to_sockets(event_data: dict):
    dead_sockets = []
    for ws in connected_websockets:
        try:
            await ws.send_json(event_data)
        except Exception:
            dead_sockets.append(ws)
    for ws in dead_sockets:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

event_bus.subscribe(broadcast_to_sockets)

routes = [
    Route("/health/live", health_live, methods=["GET"]),
    Route("/health/ready", health_ready, methods=["GET"]),
    Route("/metrics", get_metrics, methods=["GET"]),
    Route("/api/v1/alerts", ingest_alert, methods=["POST"]),
    Route("/api/v1/incidents", list_incidents, methods=["GET"]),
    Route("/api/v1/incidents/{incident_id}", get_incident, methods=["GET"]),
    Route("/api/v1/incidents/{incident_id}/postmortem", get_postmortem, methods=["GET"]),
    Route("/api/v1/playbooks", list_playbooks, methods=["GET"]),
    Route("/api/v1/chaos/inject", inject_chaos, methods=["POST"]),
    Route("/api/v1/chaos/drills", list_drills, methods=["GET"]),
    WebSocketRoute("/ws/stream", websocket_stream),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
]

app = Starlette(routes=routes, middleware=middleware)
