from __future__ import annotations

import subprocess
from pathlib import Path


def current_commit(cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def short_commit(cwd: Path | None = None) -> str | None:
    sha = current_commit(cwd)
    return sha[:7] if sha else None
