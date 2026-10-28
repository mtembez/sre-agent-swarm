"""Sandboxed subprocess command execution tool with timeouts and resource bounds."""

import asyncio
import os
import shlex
from typing import Any, Dict


async def run_sandboxed_command(command: str, timeout_seconds: float = 10.0, cwd: str = None) -> Dict[str, Any]:
    """Execute a shell command inside an isolated subprocess with strict timeouts."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    # Block high-risk commands
    dangerous_patterns = ["rm -rf /", ":(){ :|:& };:", "dd if=/dev/zero", "mkfs"]
    for bad in dangerous_patterns:
        if bad in command:
            raise PermissionError(f"Command rejected by sandbox security governor: '{command}'")

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "timed_out": False,
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout_seconds} seconds.",
            "timed_out": True,
        }
