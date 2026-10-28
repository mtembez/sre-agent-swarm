"""Synthetic health probe tool verifying service recovery and latency."""

import asyncio
import time
from typing import Any, Dict
import urllib.request
import urllib.error


async def check_service_health(target_url: str, timeout_seconds: float = 2.0) -> Dict[str, Any]:
    """Execute asynchronous non-blocking health probe against HTTP endpoint."""
    loop = asyncio.get_running_loop()

    def _sync_probe():
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "SRE-Swarm-Probe/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                elapsed = (time.perf_counter() - t0) * 1000.0
                return {
                    "is_healthy": 200 <= status_code < 300,
                    "status_code": status_code,
                    "latency_ms": round(elapsed, 2),
                    "body": body[:500],
                    "error": None,
                }
        except urllib.error.HTTPError as exc:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return {
                "is_healthy": False,
                "status_code": exc.code,
                "latency_ms": round(elapsed, 2),
                "body": "",
                "error": f"HTTPError {exc.code}: {exc.reason}",
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return {
                "is_healthy": False,
                "status_code": 0,
                "latency_ms": round(elapsed, 2),
                "body": "",
                "error": str(exc),
            }

    return await loop.run_in_executor(None, _sync_probe)
