"""Read optional notes from <notes_dir>/YYYY-MM-DD.md."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional


def read_today_notes(notes_dir: str = "./daily-notes") -> Optional[str]:
    """Return the content of today's notes file, or None if it does not exist."""
    filename = f"{date.today().isoformat()}.md"
    path = os.path.join(notes_dir, filename)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content or None
