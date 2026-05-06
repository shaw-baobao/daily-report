"""Read today's git commits from the current repository."""

from __future__ import annotations

import subprocess
from datetime import date
from typing import List


def read_today_commits(repo_path: str = ".") -> List[str]:
    """Return a list of today's commit subjects (local time)."""
    today = date.today().isoformat()
    since = f"{today} 00:00:00"
    until = f"{today} 23:59:59"

    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={since}",
                f"--until={until}",
                "--pretty=format:%h %s",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        # Empty repo (no commits yet) is not an error in this context —
        # treat it the same as "no commits today".
        if "does not have any commits yet" in stderr:
            return []
        raise RuntimeError(
            f"git log failed (exit {exc.returncode}): {stderr.strip()}"
        )

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines
