"""Log forensics analysis tool detecting error signatures and stack traces."""

import re
from typing import Any, Dict, List

# Known SRE fault patterns
PATTERN_SIGNATURES = {
    "out_of_memory": re.compile(r"(OutOfMemoryError|killed process|OOMKilled|MemoryError)", re.IGNORECASE),
    "db_pool_exhausted": re.compile(r"(PoolExhaustedError|too many connections|connection pool timeout)", re.IGNORECASE),
    "database_deadlock": re.compile(r"(Deadlock detected|Lock wait timeout exceeded|SerializationFailure)", re.IGNORECASE),
    "connection_refused": re.compile(r"(ConnectionRefusedError|upstream connect error|connection refused)", re.IGNORECASE),
    "http_502_bad_gateway": re.compile(r"(502 Bad Gateway|Bad Gateway|upstream prematurely closed)", re.IGNORECASE),
    "unhandled_exception": re.compile(r"(Traceback \(most recent call last\)|Panic: runtime error|Unhandled rejection)", re.IGNORECASE),
}


async def search_log_signatures(logs_text: str) -> List[Dict[str, Any]]:
    """Scan raw logs text and classify matching failure signatures with line context."""
    findings = []
    lines = logs_text.splitlines()

    for line_idx, line in enumerate(lines):
        for fault_type, regex in PATTERN_SIGNATURES.items():
            if regex.search(line):
                # Grab surrounding context lines
                start = max(0, line_idx - 2)
                end = min(len(lines), line_idx + 4)
                context = "\n".join(lines[start:end])

                findings.append({
                    "fault_type": fault_type,
                    "line_number": line_idx + 1,
                    "matched_text": line.strip(),
                    "context": context,
                })

    return findings
