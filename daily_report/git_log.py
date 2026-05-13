"""Read today's git commits from the current repository."""

from __future__ import annotations

import subprocess
from datetime import date
from typing import Dict, List, Optional

MAX_COMMITS_PER_DAY = 50


def _get_user_email(repo_path: str = ".") -> Optional[str]:
    """Return the git user.email configured for this repo, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "config", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _list_local_branches(repo_path: str = ".") -> List[str]:
    """Return all local branch names."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [b.strip() for b in result.stdout.splitlines() if b.strip()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []


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
    """Return a list of today's commit subjects (local time) from current branch.

    If there are more than *max_commits* commits, the list is truncated and a
    summary line "... 还有 N 条提交（已省略）" is appended.
    """
    today = date.today().isoformat()
    since = f"{today} 00:00:00"
    until = f"{today} 23:59:59"

    author_email = _get_user_email(repo_path)
    cmd = [
        "git",
        "log",
        f"--since={since}",
        f"--until={until}",
        "--pretty=format:%h %s",
    ]
    if author_email:
        cmd.append(f"--author={author_email}")

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
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


def read_today_commits_all_branches(
    repo_path: str = ".", max_commits: int = MAX_COMMITS_PER_DAY
) -> Dict[str, List[str]]:
    """Return today's commits grouped by branch, filtered by current user.

    Each commit is assigned to exactly one branch (the first one encountered).
    Returns a dict of {branch_name: [commit_lines]}.
    """
    today = date.today().isoformat()
    since = f"{today} 00:00:00"
    until = f"{today} 23:59:59"
    author_email = _get_user_email(repo_path)

    branches = _list_local_branches(repo_path)
    if not branches:
        return {}

    seen_hashes: set = set()
    result: Dict[str, List[str]] = {}

    for branch in branches:
        cmd = [
            "git",
            "-C", repo_path,
            "log",
            branch,
            f"--since={since}",
            f"--until={until}",
            "--pretty=format:%h %s",
        ]
        if author_email:
            cmd.append(f"--author={author_email}")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

        branch_commits: List[str] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            commit_hash = line.split(" ", 1)[0]
            if commit_hash in seen_hashes:
                continue
            seen_hashes.add(commit_hash)
            branch_commits.append(line)

        if branch_commits:
            if len(branch_commits) > max_commits:
                omitted = len(branch_commits) - max_commits
                branch_commits = branch_commits[:max_commits]
                branch_commits.append(f"... 还有 {omitted} 条提交（已省略）")
            result[branch] = branch_commits

    return result
