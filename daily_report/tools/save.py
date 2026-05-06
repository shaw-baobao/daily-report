"""Save a rendered daily report (read from stdin) to the given path.

Usage:
    cat report.md | python3 -m daily_report.tools.save --out-path <path>
"""

from __future__ import annotations

import argparse
import sys

from ..report import save_report


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_report.tools.save")
    parser.add_argument("--out-path", required=True, help="日报写入的绝对路径")
    args = parser.parse_args(argv)

    content = sys.stdin.read()
    if not content.strip():
        print("错误：stdin 为空，拒绝写入空日报。", file=sys.stderr)
        return 2

    path = save_report(content=content, out_path=args.out_path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
