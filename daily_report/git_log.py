"""Read today's git commits from the current repository."""

from __future__ import annotations

import subprocess
from datetime import date
from typing import List

MAX_COMMITS_PER_DAY = 50


def read_current_branch(repo_path: str = ".") -> str:
    """Return the current branch name, or 'HEAD' if detached."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch or "HEAD"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def read_today_commits(
    repo_path: str = ".", max_commits: int = MAX_COMMITS_PER_DAY
) -> List[str]:
    """Return a list of today's commit subjects (local time).

    If there are more than *max_commits* commits, the list is truncated and a
    summary line "... 还有 N 条提交（已省略）" is appended.
    """
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
    if len(lines) > max_commits:
        omitted = len(lines) - max_commits
        lines = lines[:max_commits]
        lines.append(f"... 还有 {omitted} 条提交（已省略）")
    return lines
