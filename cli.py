#!/usr/bin/env python3
"""SRE Sentinel CLI: Command-line interface for autonomous SRE swarm operations and chaos drills."""

import argparse
import asyncio
import json
import sys
from chaos.injector import ChaosInjector, ChaosType
from core.models import Alert, AlertSeverity
from core.playbooks import PLAYBOOK_REGISTRY
from core.swarm import SRESwarmOrchestrator
from telemetry.metrics import MetricsTracker


async def cmd_trigger(args):
    """Trigger the autonomous SRE swarm with an incident alert."""
    orchestrator = SRESwarmOrchestrator()
    sev = getattr(AlertSeverity, args.severity.upper(), AlertSeverity.HIGH)
    alert = Alert(
        title=args.title or f"Incident on {args.service}",
        service=args.service,
        severity=sev,
        error_message=args.error,
        raw_payload={"deployed_commit": args.commit or "head-commit"},
    )
    print(f"[CLI] Triggering SRE Swarm for service '{args.service}'...")
    state = await orchestrator.handle_alert(alert)

    print("\n" + "=" * 70)
    print(f" INCIDENT RESOLUTION SUMMARY: {state.incident_id}")
    print("=" * 70)
    print(f"Status              : {state.status.value}")
    print(f"Service             : {state.alert.service}")
    print(f"Root Cause          : {state.root_cause}")
    print(f"Remediation Action  : {state.remediation_action_taken}")
    print(f"Remediation Success : {state.remediation_success}")
    print(f"Verification Passed : {state.verification_passed}")
    print("=" * 70 + "\n")


async def cmd_chaos(args):
    """Execute automated chaos engineering drills."""
    injector = ChaosInjector()
    if args.action == "inject":
        try:
            ctype = ChaosType(args.type)
        except ValueError:
            print(f"[ERROR] Invalid chaos type '{args.type}'. Options: {[c.value for c in ChaosType]}")
            sys.exit(1)

        print(f"[CLI] Injecting chaos drill '{ctype.value}'...")
        drill = await injector.inject_fault(ctype)
        print(f"\n[CHAOS RESULT] Drill ID : {drill.drill_id}")
        print(f"               Target   : {drill.scenario.target_service}")
        print(f"               Status   : {drill.status.value}")
        print(f"               MTTR     : {drill.mttr_seconds}s\n")
    elif args.action == "list":
        print(f"Available Chaos Scenarios:")
        for c in ChaosType:
            print(f"  - {c.value}")


def cmd_playbooks(args):
    """List declarative SRE playbooks."""
    print("\n" + "=" * 70)
    print(" SRE PLAYBOOK REGISTRY")
    print("=" * 70)
    for pb in PLAYBOOK_REGISTRY.values():
        print(f"[{pb.playbook_id}] {pb.name}")
        print(f"  Match Signatures: {', '.join(pb.match_signatures)}")
        print(f"  Steps Count     : {len(pb.remediation_steps)}")
        print(f"  Verification    : {pb.post_verification_assertion}\n")


def cmd_metrics(args):
    """Display Prometheus telemetry metrics."""
    tracker = MetricsTracker.get_instance()
    print(tracker.generate_prometheus_metrics())


def main():
    parser = argparse.ArgumentParser(description="SRE Sentinel CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Trigger command
    p_trigger = subparsers.add_parser("trigger", help="Trigger SRE swarm with an alert")
    p_trigger.add_argument("--service", required=True, help="Target microservice name")
    p_trigger.add_argument("--error", required=True, help="Error message signature")
    p_trigger.add_argument("--title", help="Incident title")
    p_trigger.add_argument("--severity", default="HIGH", help="Severity level (CRITICAL, HIGH, MEDIUM, LOW)")
    p_trigger.add_argument("--commit", help="Suspect commit SHA")

    # Chaos command
    p_chaos = subparsers.add_parser("chaos", help="Run chaos engineering drills")
    p_chaos.add_argument("action", choices=["inject", "list"], help="Chaos action")
    p_chaos.add_argument("--type", default="db_pool_starvation", help="Chaos scenario type")

    # Playbooks command
    subparsers.add_parser("playbooks", help="List declarative SRE playbooks")

    # Metrics command
    subparsers.add_parser("metrics", help="Display telemetry metrics")

    args = parser.parse_args()

    if args.command == "trigger":
        asyncio.run(cmd_trigger(args))
    elif args.command == "chaos":
        asyncio.run(cmd_chaos(args))
    elif args.command == "playbooks":
        cmd_playbooks(args)
    elif args.command == "metrics":
        cmd_metrics(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
