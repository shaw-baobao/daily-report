"""Collect today's git commits + optional notes and emit JSON on stdout.

Usage:
    python3 -m daily_report.tools.collect --repo "$PWD"

Output schema (single JSON object on stdout):
{
  "date": "YYYY-MM-DD",
  "repo_name": "<git-toplevel-basename>",
  "commits": ["<hash> <subject>", ...],   # today's commits, incl. merges
  "notes": "<raw markdown>" | null,        # contents of notes file if any
  "notes_path": "<abs path>",              # where the notes file is expected
  "out_path": "<abs path>"                 # where the final report should be saved
}
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date

from ..git_log import read_today_commits
from ..notes import read_today_notes


DEFAULT_ROOT = os.path.expanduser("~/.dailyreport")


def _resolve_repo_name(repo: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        toplevel = result.stdout.strip()
        if toplevel:
            return os.path.basename(toplevel)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return os.path.basename(os.path.abspath(repo)) or "unknown-repo"


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_report.tools.collect")
    parser.add_argument("--repo", required=True, help="Git 仓库路径（通常传 $PWD）")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="产物根目录，默认 ~/.dailyreport")
    args = parser.parse_args(argv)

    today = date.today().isoformat()
    repo_name = _resolve_repo_name(args.repo)

    notes_dir = os.path.join(args.root, "notes", repo_name)
    notes_path = os.path.join(notes_dir, f"{today}.md")
    out_path = os.path.join(args.root, "reports", repo_name, f"{today}.md")

    commits = read_today_commits(repo_path=args.repo)
    notes = read_today_notes(notes_dir=notes_dir)

    payload = {
        "date": today,
        "repo_name": repo_name,
        "commits": commits,
        "notes": notes,
        "notes_path": notes_path,
        "out_path": out_path,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
