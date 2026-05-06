# daily-report

**入口**：这是一个 Cursor / Claude Code / Codex 的 **Skill**，不是 CLI。  
你在对话里说"写今天的日报"/"生成日报"，Skill 会：

1. 读取当前 git 仓库今日 commits（含 merge）
2. 读取可选备注 `~/.dailyreport/notes/<repo>/YYYY-MM-DD.md`
3. **由对话中的 LLM 用中文归纳**为「今日工作 / 问题与风险 / 明日计划」三段
4. 展示草稿并等你调整，确认后落盘到 `~/.dailyreport/reports/<repo>/YYYY-MM-DD.md`
5. 询问发送目标（飞书群 chat_id 或个人 open_id），确认后通过 `lark-cli im +messages-send` 发送

归纳能力来自你对话里的 LLM，不依赖任何 API key。

## 目录结构

```
daily-report/
├── daily_report/                   # 数据与发送层（确定性操作）
│   ├── git_log.py                  # 读今日 commits（保留 merge）
│   ├── notes.py                    # 读备注文件
│   ├── report.py                   # save_report: 写盘
│   ├── sender.py                   # ReportSender + FeishuSender（lark-cli 后端）
│   └── tools/
│       ├── collect.py              # 输出 JSON: {date, repo_name, commits, notes, out_path, ...}
│       ├── save.py                 # stdin markdown → 写盘
│       └── send.py                 # stdin markdown → lark-cli 发送
├── skills/daily-report/SKILL.md    # Skill 指令（分发主体）
├── README.md
└── requirements.txt                # 空（零依赖）
```

## 产物位置

```
~/.dailyreport/
├── reports/<repo-name>/YYYY-MM-DD.md   # 日报
└── notes/<repo-name>/YYYY-MM-DD.md     # 备注（可选手写）
```

`<repo-name>` 取自 `git rev-parse --show-toplevel` 的 basename。

## 安装（本机）

```bash
# 1. clone / 放到某个稳定路径
git clone <url> ~/Documents/company/daily-report    # 或你偏好的路径

# 2. 把 skill 软链进各客户端的 skills 目录（三选 N）
ln -s ~/Documents/company/daily-report/skills/daily-report  ~/.cursor/skills/daily-report
ln -s ~/Documents/company/daily-report/skills/daily-report  ~/.claude/skills/daily-report
ln -s ~/Documents/company/daily-report/skills/daily-report  ~/.codex/skills/daily-report
```

SKILL.md 会自动尝试定位 Python 包根：优先读环境变量 `DAILY_REPORT_PACKAGE`，否则依次尝试 `~/Documents/company/daily-report`、`~/daily-report`。如果你放在其他位置，在 shell 启动文件里 `export DAILY_REPORT_PACKAGE=/your/path`。

## 分发给同事

同事只要：

1. clone 本仓库到任意位置
2. 选一个客户端，把 `skills/daily-report/` 软链到对应 skills 目录（同上）
3. 确保 `lark-cli` 已安装并 `lark-cli auth login` 完成（参考 `lark-shared` skill）

**不需要任何 API key**。归纳由他们对话里的 LLM 负责。

## 使用

在 Cursor / Claude Code / Codex 对话里，位于任意 git 仓库目录下，说：

> 帮我写今天的日报

Skill 会按 SKILL.md 的工作流自动走完收集 → 归纳 → 展示 → 落盘 → 询问发送目标 → 发送。你有机会在"展示"和"询问发送目标"两个关卡干预。

## 手工备注格式（可选）

提前在 `~/.dailyreport/notes/<repo>/YYYY-MM-DD.md` 写一些 LLM 看不到的信息（会议、口头讨论、风险感知），Skill 会把这些内容**优先于** commit 归纳结果写进日报：

```markdown
## 今日工作
- 和 X 口头对齐了 Y 方案

## 问题与风险
- Z 模块有回归风险

## 明日计划
- 推进 W
```

未标题化的段落会被归到"今日工作"自由块。

## 替换发送后端

`ReportSender` 是抽象基类，`FeishuSender` 是 lark-cli 实现。要接入别的渠道（企业微信、钉钉、邮件等）：

```python
from daily_report.sender import ReportSender

class SlackSender(ReportSender):
    def send(self, content: str) -> None:
        ...
```

在 `tools/send.py` 里按需切换即可。当前 Skill 只编排 `FeishuSender`。

## 需求映射

| # | 需求 | 实现 |
|---|------|------|
| 1 | 读当前 repo 今日 commits | `daily_report/git_log.py`（含 merge）|
| 2 | 读可选备注 | `daily_report/notes.py` + `collect.py` 默认路径 |
| 3 | 中文三段结构 | `SKILL.md` 的归纳规则 + LLM |
| 4 | 保存到 `./daily-reports/YYYY-MM-DD.md` | 升级为 `~/.dailyreport/reports/<repo>/YYYY-MM-DD.md`，按仓库归档（用户决策） |
| 5 | 终端打印草稿 | Skill 在对话里展示 markdown |
| 6 | 发送前确认 | Skill 第 3、5、6 步三道关卡 |
| 7 | ReportSender 抽象 + FeishuSender 可替换 | `sender.py` 保持 ABC + 具体实现分层 |
| 8 | 未确认不自动发送 | SKILL.md "不变量" 章节强制规定 |
