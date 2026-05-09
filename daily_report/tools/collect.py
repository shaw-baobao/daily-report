"""Collect today's git commits + optional notes and emit JSON on stdout.

Two modes:

1. Single-repo (backward compatible):
       python3 -m daily_report.tools.collect --repo "$PWD"

   Output:
   {
     "mode": "single",
     "date": "YYYY-MM-DD",
     "repo_name": "<git-toplevel-basename>",
     "commits": ["<hash> <subject>", ...],
     "notes": "<raw markdown>" | null,
     "notes_path": "<abs path>",
     "out_path": "<abs path>"
   }

2. Workspace (multi-repo):
       python3 -m daily_report.tools.collect --scan "$HOME/Documents/company"
       python3 -m daily_report.tools.collect --repo path/A --repo path/B

   Scans one level deep for git work-trees, keeps only repos with
   today's commits (Q2:B), groups them under a single workspace payload.

   Output:
   {
     "mode": "workspace",
     "date": "YYYY-MM-DD",
     "workspace_name": "<parent-dir-basename>",
     "repos": [
       {"repo_name": "<name>", "repo_path": "<abs path>",
        "commits": ["<hash> <subject>", ...]},
       ...
     ],
     "notes": "<raw markdown>" | null,
     "notes_path": "<abs path>",
     "out_path": "<abs path>"
   }
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from typing import Optional

from ..git_log import read_current_branch, read_today_commits
from ..notes import read_today_notes


DEFAULT_ROOT = os.path.expanduser("~/.dailyreport")
WORKSPACE_PREFIX = "_workspace_"


def _git_toplevel(path: str) -> Optional[str]:
    """Return the git work-tree root for `path`, or None if not a repo."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        toplevel = result.stdout.strip()
        return toplevel or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _resolve_repo_name(repo: str) -> str:
    toplevel = _git_toplevel(repo)
    if toplevel:
        return os.path.basename(toplevel)
    return os.path.basename(os.path.abspath(repo)) or "unknown-repo"


def _scan_workspace(workspace: str) -> list[str]:
    """Return absolute paths of first-level subdirs that are git work-trees.

    Only the immediate children are inspected (Q1:A, no recursion into
    nested node_modules / vendored submodules).
    """
    workspace = os.path.abspath(workspace)
    if not os.path.isdir(workspace):
        raise RuntimeError(f"workspace 不存在或不是目录：{workspace}")

    repos: list[str] = []
    for entry in sorted(os.listdir(workspace)):
        if entry.startswith("."):
            continue
        child = os.path.join(workspace, entry)
        if not os.path.isdir(child):
            continue
        if os.path.isdir(os.path.join(child, ".git")):
            repos.append(child)
    return repos


def _build_single(repo: str, root: str, today: str) -> dict:
    repo_name = _resolve_repo_name(repo)
    notes_dir = os.path.join(root, "notes", repo_name)
    notes_path = os.path.join(notes_dir, f"{today}.md")
    out_path = os.path.join(root, "reports", repo_name, f"{today}.md")
    commits = read_today_commits(repo_path=repo)
    branch = read_current_branch(repo_path=repo)
    notes = read_today_notes(notes_dir=notes_dir)
    return {
        "mode": "single",
        "date": today,
        "repo_name": repo_name,
        "branch": branch,
        "commits": commits,
        "notes": notes,
        "notes_path": notes_path,
        "out_path": out_path,
    }


def _build_workspace(
    repo_paths: list[str],
    workspace_name: str,
    root: str,
    today: str,
) -> dict:
    repos_payload: list[dict] = []
    for repo_path in repo_paths:
        commits = read_today_commits(repo_path=repo_path)
        if not commits:
            continue  # Q2:B — skip repos with no commits today
        repos_payload.append(
            {
                "repo_name": _resolve_repo_name(repo_path),
                "repo_path": os.path.abspath(repo_path),
                "branch": read_current_branch(repo_path=repo_path),
                "commits": commits,
            }
        )

    archive_key = WORKSPACE_PREFIX + workspace_name
    notes_dir = os.path.join(root, "notes", archive_key)
    notes_path = os.path.join(notes_dir, f"{today}.md")
    out_path = os.path.join(root, "reports", archive_key, f"{today}.md")
    notes = read_today_notes(notes_dir=notes_dir)

    return {
        "mode": "workspace",
        "date": today,
        "workspace_name": workspace_name,
        "repos": repos_payload,
        "notes": notes,
        "notes_path": notes_path,
        "out_path": out_path,
    }


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_report.tools.collect")
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Git 仓库路径，可重复传入多个。传 1 个 → single 模式；传 >=2 个 → workspace 模式。",
    )
    parser.add_argument(
        "--scan",
        default=None,
        help="工作区目录（如 ~/Documents/company）；扫描一级子目录，纳入今日有提交的仓库。",
    )
    parser.add_argument(
        "--workspace-name",
        default=None,
        help="workspace 归档名，默认取 --scan 目录的 basename。多 --repo 时必传或用默认 'workspace'。",
    )
    parser.add_argument("--root", default=DEFAULT_ROOT, help="产物根目录，默认 ~/.dailyreport")
    args = parser.parse_args(argv)

    if not args.repo and not args.scan:
        parser.error("必须至少提供 --repo 或 --scan")

    today = date.today().isoformat()

    # --scan expands to a list of --repo values
    scanned: list[str] = []
    if args.scan:
        scanned = _scan_workspace(args.scan)

    repo_paths = list(dict.fromkeys(args.repo + scanned))  # dedupe, preserve order

    if len(repo_paths) == 0 and args.scan:
        # Scanned a dir but no subrepos at all (not even ones with no commits)
        parser.error(f"{args.scan} 下一级目录没有发现 git 仓库")

    if len(repo_paths) == 1 and not args.scan:
        payload = _build_single(repo_paths[0], args.root, today)
    else:
        if args.workspace_name:
            workspace_name = args.workspace_name
        elif args.scan:
            workspace_name = os.path.basename(os.path.abspath(args.scan))
        else:
            workspace_name = "workspace"
        payload = _build_workspace(repo_paths, workspace_name, args.root, today)

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
