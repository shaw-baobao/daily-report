"""Send a rendered daily report (read from stdin) via FeishuSender / lark-cli.

Usage (pick one target flag):
    cat report.md | python3 -m daily_report.tools.send --chat-id oc_xxx
    cat report.md | python3 -m daily_report.tools.send --user-id ou_xxx

Options:
    --text        send as plain text instead of markdown (default: markdown)
    --dry-run     do not actually call lark-cli; print what would be sent

The Skill is responsible for obtaining user confirmation BEFORE invoking
this command. This module performs the actual send unconditionally once
invoked.
"""

from __future__ import annotations

import argparse
import sys

from ..sender import FeishuSender, ReportSender


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_report.tools.send")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--chat-id", dest="chat_id", help="飞书群 chat_id (oc_xxx)")
    group.add_argument("--user-id", dest="user_id", help="飞书用户 open_id (ou_xxx)")
    parser.add_argument(
        "--text",
        action="store_true",
        help="按纯文本发送；默认按 markdown 发送（lark-cli 会自动排版）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要发送的目标和内容，不调用 lark-cli",
    )
    args = parser.parse_args(argv)

    content = sys.stdin.read()
    if not content.strip():
        print("错误：stdin 为空，拒绝发送空日报。", file=sys.stderr)
        return 2

    if args.chat_id:
        kind, target = "chat", args.chat_id
    else:
        kind, target = "user", args.user_id

    content_mode = "text" if args.text else "markdown"

    if args.dry_run:
        print(f"[dry-run] 目标={kind}:{target} 模式={content_mode}")
        print("-" * 40)
        print(content)
        print("-" * 40)
        return 0

    sender: ReportSender = FeishuSender(
        target_kind=kind, target_id=target, content_mode=content_mode
    )
    try:
        sender.send(content)
    except Exception as exc:
        print(f"发送失败：{exc}", file=sys.stderr)
        return 1

    print(f"已发送至 {kind}:{target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
