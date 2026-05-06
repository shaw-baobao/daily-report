"""Persist a rendered daily report to disk.

The report *content* is assembled by the LLM inside the Skill,
not by this module. This module only persists what it is given.
"""

from __future__ import annotations

import os


def save_report(content: str, out_path: str) -> str:
    """Write `content` to `out_path`, creating parent dirs as needed.

    Returns the absolute path of the written file.
    """
    out_path = os.path.abspath(os.path.expanduser(out_path))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path
