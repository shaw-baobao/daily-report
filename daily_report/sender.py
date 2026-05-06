"""Report sender abstraction with a lark-cli based Feishu implementation."""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Literal, Optional


class ReportSender(ABC):
    """Abstract sender. Implementations must not perform any I/O in __init__
    that could send data before send() is explicitly invoked.
    """

    @abstractmethod
    def send(self, content: str) -> None:
        """Send the report. Raise on failure."""
        raise NotImplementedError


class FeishuSender(ReportSender):
    """Feishu sender backed by the local `lark-cli` tool.

    Does NOT hardcode a recipient. The Skill must decide (possibly by asking
    the user) who/where to send the report to, and pass that choice here.

    Parameters
    ----------
    target_kind : {"chat", "user"}
        "chat"  -> send to a group chat identified by chat_id
        "user"  -> send to a single user identified by open_id/user_id/email
    target_id : str
        The chat_id or user identifier accepted by `lark-cli im +send`.
    lark_cli : str, optional
        Override the lark-cli binary path. Defaults to "lark-cli" on PATH.
    """

    def __init__(
        self,
        target_kind: Literal["chat", "user"],
        target_id: str,
        lark_cli: Optional[str] = None,
        content_mode: Literal["markdown", "text"] = "markdown",
    ) -> None:
        if target_kind not in ("chat", "user"):
            raise ValueError(f"target_kind must be 'chat' or 'user', got {target_kind!r}")
        if not target_id:
            raise ValueError("target_id must be non-empty")
        if content_mode not in ("markdown", "text"):
            raise ValueError(f"content_mode must be 'markdown' or 'text', got {content_mode!r}")
        self.target_kind = target_kind
        self.target_id = target_id
        self.content_mode = content_mode
        self.lark_cli = lark_cli or shutil.which("lark-cli") or "lark-cli"

    def send(self, content: str) -> None:
        if not shutil.which(self.lark_cli) and self.lark_cli == "lark-cli":
            raise RuntimeError(
                "未找到 lark-cli，请先安装并通过 `lark-cli auth login` 登录。"
            )

        target_flag = "--chat-id" if self.target_kind == "chat" else "--user-id"
        content_flag = f"--{self.content_mode}"
        cmd = [
            self.lark_cli,
            "im",
            "+messages-send",
            target_flag,
            self.target_id,
            content_flag,
            content,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"lark-cli 发送失败 (exit {result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
