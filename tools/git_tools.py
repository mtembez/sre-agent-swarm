"""Git inspection tool correlating commits and diffs with incident timestamps."""

import asyncio
from typing import Any, Dict, List


async def get_recent_commits(repo_path: str = ".", count: int = 5) -> List[Dict[str, str]]:
    """Retrieve recent git commits formatted as structured dictionaries."""
    cmd = f'git -C "{repo_path}" log -n {count} --pretty=format:"%h|%an|%ar|%s"'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    commits = []
    if proc.returncode == 0:
        for line in stdout.decode("utf-8").splitlines():
            parts = line.strip().split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "sha": parts[0],
                    "author": parts[1],
                    "relative_time": parts[2],
                    "message": parts[3],
                })
    return commits


async def inspect_commit_diff(repo_path: str = ".", commit_sha: str = "HEAD") -> str:
    """Retrieve stat and diff for a specific git commit."""
    cmd = f'git -C "{repo_path}" show --stat {commit_sha}'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8") if proc.returncode == 0 else "Failed to retrieve git diff."
